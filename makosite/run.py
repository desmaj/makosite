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
@click.argument('siteroot', type=click.Path())
def build(siteroot):
    siteconfig = SiteConfig(siteroot)
    builder = SiteBuilder(siteconfig)
    builder.build()
