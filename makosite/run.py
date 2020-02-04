import json
import os

import click

from makosite import SiteBuilder
from makosite import SiteConfig


OUTPUT_DIR = 'public'


@click.group()
def main():
    if not os.path.isdir(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)


@main.command()
@click.argument('config-path', type=click.Path())
@click.option('-b', '--build-dir', type=click.Path())
def build(config_path, build_dir):
    with open(config_path, 'r') as config_file:
        config = json.loads(config_file.read())
    siteconfig = SiteConfig(config)
    builder = SiteBuilder(siteconfig)
    builder.build()
