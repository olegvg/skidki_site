# -*- coding: utf-8 -*-

import os.path
import sys


def add_path():
    selfpath = os.path.dirname(os.path.abspath(__file__))
    rootpath = os.path.join(selfpath, '..')
    sys.path.append(rootpath)


if __name__ == '__main__':
    add_path()

    from scraper import cli
    cli()
