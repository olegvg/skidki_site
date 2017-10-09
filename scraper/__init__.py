# -*- coding: utf-8 -*-

from __future__ import print_function

import gevent.monkey
gevent.monkey.patch_all()

import click
from scraper.lib import utils
from scraper.scrapers import scrapers


@click.command()
@click.option('-s', '--scraper', type=click.Choice(scrapers.keys()), help='Specify scraper name to run.')
def run(scraper):
    utils.init_root_logger()
    utils.init_db()

    scraper_cls = scrapers[scraper]
    scraper_cls().run()


@click.group()
@click.option('--config', default='scraper_config.yml', help='YML-config file.')
def init(config):
    utils.config_loader(config)


def cli():
    init.add_command(run)
    init()
