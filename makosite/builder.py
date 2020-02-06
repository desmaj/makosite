from collections import namedtuple
import datetime
import fnmatch
import glob
import json
import operator
import os
import shutil

from bs4 import BeautifulSoup
from mako.template import Template
from mako.lookup import TemplateLookup


CONFIG_FILENAME = '__config__.json'
LAYOUT_FILENAME = '__layout__.html'
MAKO_TEMPLATE_PATTERN = '*.html'
MARKDOWN_TEMPLATE_PATTERN = '*.md'

ISODATE = "%Y-%m-%dT%H:%M:%S"

DirectoryContents = namedtuple(
    'DirectoryContents',
    ['dirnames', 'filenames'],
)


class SiteConfig(object):

    def __init__(self, config_json):
        self._config = config_json

        self.siteroot = config_json.get('siteroot', 'content')
        self.buildroot = config_json.get('buildroot', 'build')
        self.siteurl = config_json['siteurl']
        self.ignored = config_json.get('ignored', [])
        self.static = config_json.get('static', [])

        self.buildtime = datetime.datetime.now()
        self.buildtemp = '.build-tmp'

    def format_path(self, path):
        if (
                self.is_content_item(path) and
                not self.is_static(path) and
                self._config.get('rewrite-urls')
        ):
            path = os.path.join(path[:-5], 'index.html')
        return path

    def output_path(self, path):
        outpath = os.path.join(
            self.buildtemp,
            os.path.relpath(path, self.siteroot),
        )
        outpath = self.format_path(outpath)
        outdir = os.path.dirname(outpath)
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        return outpath

    @property
    def title(self):
        return self._config.get('title')

    @property
    def description(self):
        return self._config.get('description')

    @property
    def author(self):
        return self._config.get('author')

    def is_content_item(self, filepath):
        filename = os.path.basename(filepath)
        return (
            filename.endswith(".html") and
            filename not in [
                'index.html',
                '__layout__.html',
                '__page__.html',
            ]
        )

    def is_ignored(self, filepath):
        filename = os.path.basename(filepath)
        if filename.startswith('__'):
            return True
        filepath = os.path.relpath(filepath, self.siteroot)
        for pattern in self.ignored:
            if fnmatch.fnmatch(filepath, pattern):
                return True
        return False

    def is_static(self, filepath):
        filepath = os.path.relpath(filepath, self.siteroot)
        for pattern in self.static:
            if fnmatch.fnmatch(filepath, pattern):
                return True
        return False


class PageConfig(object):

    def __init__(self, config):
        self._config = config

    def __getattr__(self, attr):
        return getattr(self._config, attr, None)


class ContentItem(object):

    def __init__(self, template, context):
        self._template = template
        self._context = context

    @property
    def metadata(self):
        return self._template.module

    @property
    def title(self):
        metadata = self.metadata
        return getattr(metadata, 'title', None)

    @property
    def date(self):
        metadata = self.metadata
        datestr = getattr(metadata, 'date', None)
        if datestr:
            return datetime.datetime.strptime(datestr, ISODATE)

    def summarize(self):
        rendered_text = self.contents()
        soup = BeautifulSoup(rendered_text, 'html.parser')
        paragraphs = soup.find_all('p')
        summary = BeautifulSoup("<div/>", 'html.parser')
        while len(str(summary)) < 400 and paragraphs:
            summary.append(paragraphs.pop(0))
        return summary

    def contents(self, length=None):
        text = self._template.render(**self._context.params())
        if length is not None:
            text = text[:length]
        return text


class DirectoryContext(object):

    def __init__(self, site, path):
        self.site = site
        self._path = path
        self.config = None

        config_path = os.path.join(self._path, CONFIG_FILENAME)
        if os.path.exists(config_path):
            with open(config_path, 'r') as config_file:
                self.config = json.loads(config_file.read())

    @property
    def path(self):
        return self._path

    @property
    def content_path(self):
        return os.path.relpath(self._path, self.site.siteroot)

    def filepath(self, filepath):
        return os.path.join(self._path, filepath)

    def output_path(self, filepath=None):
        path = self._path
        if filepath is not None:
            path = os.path.join(path, filepath)
        return self.site.output_path(path)

    def contents(self):
        dirnames = []
        filenames = []

        files_to_skip = [LAYOUT_FILENAME]
        for direntry in os.listdir(self._path):
            if os.path.isdir(os.path.join(self._path, direntry)):
                dirnames.append(direntry)
            elif direntry not in files_to_skip:
                filenames.append(direntry)

        return DirectoryContents(dirnames, filenames)

    def paginate(self):
        return self.config and self.config.get('paginate')

    def url(self, resource_path=None):
        if not resource_path:
            return self.site.siteurl

        if resource_path.startswith('/'):
            resource_path = resource_path[1:]
        else:
            resource_path = '/'.join([self._path, resource_path])
        resource_path = self.site.format_path(resource_path)
        if os.path.basename(resource_path) == 'index.html':
            resource_path = os.path.dirname(resource_path)
        return '{}{}'.format(self.site.siteurl, resource_path)

    def items(self, pattern=None, limit=None, order=None, reversed=False):
        if pattern is None:
            pattern = '*'
        if order is None:
            order = 'date'
        content_pattern = os.path.join(self.site.siteroot, pattern)
        matching_items = [
            filepath
            for filepath in glob.glob(content_pattern)
            if (
                    not os.path.isdir(filepath) and
                    self.site.is_content_item(filepath) and
                    not self.site.is_ignored(filepath)
            )
        ]

        directory_contexts = {}

        matches = []
        for filepath in matching_items:
            dirpath = os.path.dirname(filepath)
            if dirpath not in directory_contexts:
                directory_contexts[dirpath] = DirectoryContext(
                    self.site,
                    dirpath,
                )
            item_url = self.url("/" + os.path.relpath(filepath, self.site.siteroot))
            with open(filepath, 'r') as item_file:
                item_context = PageContext(
                    os.path.basename(filepath).rsplit('.', 1)[1],
                    directory_contexts[dirpath],
                    directory_contexts[dirpath].config,
                )
                item_str = item_file.read()
                matches.append(
                    (
                        item_url,
                        ContentItem(Template(item_str), item_context)
                    )
                )

        matches = sorted(
            matches,
            key=lambda match: getattr(match[1].metadata, order),
            reverse=reversed,
        )

        if limit is not None:
            matches = matches[:limit]

        return matches

    def params(self):
        return {
            'url': self.url,
            'name': os.path.basename(self._path),
            'items': self.items,
            'site': self.site,
            'path': self._path,
            'now': self.site.buildtime,
        }


class PaginationContext(object):

    def __init__(self, page_number, page_count, page_items, parent):
        self.page_number = page_number
        self.page_count = page_count
        self.page_items = page_items
        self.parent = parent

    @property
    def config(self):
        return self.parent.config

    def params(self):
        prev_page = None
        if self.page_number < self.page_count:
            prev_page = self.page_number + 1
        next_page = None
        if self.page_number > 1:
            next_page = self.page_number - 1
        params = self.parent.params()
        params.update(
            {
                'page_number': self.page_number,
                'page_items': self.page_items,
                'prev_page': prev_page,
                'next_page': next_page,
            }
        )
        return params


class PageContext(object):

    def __init__(self, path, parent, config):
        self.path = path
        self.name = os.path.basename(self.path)
        self.parent = parent
        self.config = config

    def params(self):
        params = self.parent.params()
        params.update(
            {'name': self.name, 'dirpath': params['path']}
        )
        return params


class SiteBuilder(object):

    def __init__(self, siteconfig):
        self._siteconfig = siteconfig
        self._lookup = TemplateLookup(directories=[siteconfig.siteroot])

    def _is_mako_template(self, filename):
        return fnmatch.fnmatch(filename, MAKO_TEMPLATE_PATTERN)

    def _lookup_path(self, path):
        return os.path.relpath(path, self._siteconfig.siteroot)

    def _render_content(self, filepath, context, layout_path):
        if self._is_mako_template(os.path.basename(filepath)):
            return self._render_template(filepath, context, layout_path)
        else:
            with open(filepath, 'rb') as content_file:
                return content_file.read()

    def _render_template(self, filepath, context, layout_path):
        with open(filepath, 'r') as template_file:
            template_str = template_file.read()
        if layout_path:
            template_str = (
                '<%inherit file="{}" />\n{}'
                .format(
                    layout_path,
                    template_str,
                )
            )
        try:
            template = Template(template_str, lookup=self._lookup)
            params = context.params()
            return template.render(**params).encode('utf8')
        except Exception:
            print('Failed to render source file {!r}'.format(filepath))
            print(template_str)
            raise

    def _render_page(
            self,
            directory_context,
            page_number,
            page_count,
            items,
            layout_path,
    ):
        page_context = PaginationContext(
            page_number,
            page_count,
            items,
            directory_context,
        )
        template_path = directory_context.filepath('__page__.html')
        return self._render_template(template_path, page_context, layout_path)

    def _paginate(self, directory_context, layout_path):
        items_per_page = directory_context.paginate()
        if items_per_page:
            directory_item_pattern = (
                '{}/*'
                .format(directory_context.content_path)
            )
            directory_items = directory_context.items(
                directory_item_pattern,
                reversed=True,
            )
            directory_item_count = len(directory_items)
            page_count = directory_item_count // items_per_page
            if directory_item_count % items_per_page > 0:
                page_count += 1
            base_item_index = 0
            for page_index in range(page_count):
                next_page_item_index = base_item_index+items_per_page
                page_items = directory_items[base_item_index:next_page_item_index]
                page_contents = self._render_page(
                    directory_context,
                    page_number=page_index+1,
                    page_count=page_count,
                    items=page_items,
                    layout_path=layout_path,
                )
                if page_index == 0:
                    index_page_path = directory_context.output_path('index.html')
                    with open(index_page_path, 'wb') as index_page_file:
                        index_page_file.write(page_contents)

                page_path = directory_context.output_path(
                    os.path.join(str(page_index+1), 'index.html')
                )
                page_dir = os.path.dirname(page_path)
                if not os.path.exists(page_dir):
                    os.makedirs(page_dir)
                with open(page_path, 'wb') as page_file:
                    page_file.write(page_contents)
                base_item_index += items_per_page

    def _build_directory(self, dirpath, layout_lookup):
        if self._siteconfig.is_ignored(dirpath):
            return

        dir_context = DirectoryContext(
            site=self._siteconfig,
            path=dirpath,
        )
        if self._siteconfig.is_static(dirpath):
            output_dirpath = dir_context.output_path()
            shutil.copytree(dirpath, output_dirpath)
        else:
            if not os.path.exists(dir_context.output_path()):
                os.mkdir(dir_context.output_path())

            dir_contents = dir_context.contents()

            layout_path = os.path.join(dirpath, LAYOUT_FILENAME)
            if os.path.exists(layout_path):
                layout_lookup_path = self._lookup_path(layout_path)
                layout_lookup[dirpath] = layout_lookup_path
                for dirname in dir_contents.dirnames:
                    subdir_path = os.path.join(dirpath, dirname)
                    layout_lookup[subdir_path] = layout_lookup_path
            else:
                layout_lookup_path = layout_lookup[os.path.dirname(dirpath)]

            self._paginate(dir_context, layout_lookup_path)

            for filename in dir_contents.filenames:
                if filename == LAYOUT_FILENAME:
                    continue

                filepath = os.path.join(dirpath, filename)
                output_path = dir_context.output_path(filename)

                if self._siteconfig.is_ignored(filepath):
                    continue
                elif self._siteconfig.is_static(filepath):
                    shutil.copy(filepath, output_path)
                else:
                    context = PageContext(
                        os.path.basename(filepath).rsplit('.', 1)[0],
                        dir_context,
                        dir_context.config,
                    )
                    result = self._render_content(
                        filepath,
                        context,
                        layout_lookup_path,
                    )
                    with open(output_path, 'wb') as output_file:
                        output_file.write(result)

            for dirname in dir_contents.dirnames:
                self._build_directory(
                    os.path.join(dirpath, dirname),
                    layout_lookup,
                )

    def build(self):
        if os.path.exists(self._siteconfig.buildtemp):
            shutil.rmtree(self._siteconfig.buildtemp)
        os.mkdir(self._siteconfig.buildtemp)

        directory_layout_lookup = {self._siteconfig.siteroot: None}

        self._build_directory(
            self._siteconfig.siteroot,
            directory_layout_lookup,
        )

        if os.path.exists(self._siteconfig.buildroot):
            shutil.rmtree(self._siteconfig.buildroot)
        os.rename(self._siteconfig.buildtemp, self._siteconfig.buildroot)
