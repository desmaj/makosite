import json
import os

import click
from markdown import markdown
import yaml


@click.group()
def main():
    pass


@main.command('markdown')
@click.argument('site-root', type=click.Path())
@click.argument(
    'destination-path',
    type=click.Path(exists=True, file_okay=False),
)
def import_markdown(site_root, destination_path):
    for dirpath, dirnames, filenames in os.walk(site_root):
        if dirpath == site_root:
            destination_dirpath = destination_path
        else:
            destination_dirpath = os.path.join(
                destination_path,
                os.path.relpath(dirpath, site_root),
            )
        if not os.path.exists(destination_dirpath):
            os.mkdir(destination_dirpath)

        for filename in filenames:
            if filename.endswith('.md'):
                filepath = os.path.join(dirpath, filename)
                destination_filepath = os.path.join(
                    destination_dirpath,
                    '{}.{}'.format(filename[:-3], 'html')
                )
                with open(filepath, 'r') as markdown_file:
                    markdown_lines = markdown_file.read().splitlines()

                    if markdown_lines[0] == '---':
                        header_end = markdown_lines[1:].index('---')+1
                        header = '\n'.join(markdown_lines[1:header_end])
                        metadata = yaml.load(header)
                        metadata_filepath = (
                            '{}.{}'
                            .format(destination_filepath, 'json')
                        )
                        with open(metadata_filepath, 'w') as metadata_file:
                            metadata_file.write(json.dumps(metadata, indent=2))

                        markdown_lines = markdown_lines[header_end+1:]

                    markdown_content = '\n'.join(markdown_lines)

                    html_result = markdown(markdown_content)
                with open(destination_filepath, 'w') as destination_file:
                    destination_file.write(html_result)
