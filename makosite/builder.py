import fnmatch
import json
import os

from mako.template import Template
from mako.lookup import TemplateLookup


MAKO_TEMPLATE_PATTERN = '*.html'
MARKDOWN_TEMPLATE_PATTERN = '*.md'


class SiteConfig(object):

    def __init__(self, siteroot, siteurl=None, buildroot=None, ignores=None):
        self.siteroot = siteroot
        self.siteurl = siteurl if siteurl is not None else ''
        self.buildroot = buildroot if buildroot is not None else 'build'
        self.ignores = ignores if ignores is None else ignores


class DirectoryContext(object):

    def __init__(self, path, config, parent=None):
        self._path = path
        self._config = config
        self._parent = parent

    def url(self, resource_path):
        if resource_path.startswith('/'):
            resource_path = '/'.join([self._path, resource_path])
        return '{}{}'.format(self._config.siteurl, resource_path)

    def params(self, dirpath):
        return {
            'url': self.url,
            'siteurl': self._config.siteurl,
            'dirpath': dirpath,
        }


class SiteBuilder(object):

    def __init__(self, siteconfig):
        self._siteconfig = siteconfig
        self._lookup = TemplateLookup(directories=[siteconfig.siteroot])

    def _is_mako_template(self, filename):
        return fnmatch.fnmatch(filename, MAKO_TEMPLATE_PATTERN)

    def build(self):
        for dirpath, dirnames, filenames in os.walk(self._siteconfig.siteroot):
            layout = '__layout__' in filenames
            context = DirectoryContext(dirpath, config=self._siteconfig)

            for filename in filenames:
                if filename == '__layout__':
                    continue

                filepath = os.path.join(dirpath, filename)
                output_path = os.path.join(
                    self._siteconfig.buildroot,
                    dirpath,
                    filename,
                )
                if self._is_mako_template(filename):
                    with open(filepath, 'rb') as template_file:
                        template_str = template_file.read()
                    if layout:
                        template_str = (
                            '<inherit file="__layout__" />\n{}'
                            .format(template_str)
                        )

                    template = Template(template_str, lookup=self._lookup)
                    result = template.render(**context.params(dirpath))
                    with open(output_path, 'wb') as output_file:
                        output_file.write(result)
                else:
                    with open(output_path, 'wb') as output_file:
                        with open(filepath, 'rb') as input_file:
                            output_file.write(input_file.read())
