import click

from makosite import SiteBuilder
from makosite import SiteConfig


@click.group()
def main():
    pass


@main.command()
@click.argument('config-path', type=click.Path())
def build(config_path):
    siteconfig = SiteConfig.load(config_path)
    builder = SiteBuilder(siteconfig)
    builder.build()
