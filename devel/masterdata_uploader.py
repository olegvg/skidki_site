# -*- coding: utf-8 -*-

from scraper.lib import utils
from commonlib import masterdata


if __name__ == "__main__":
    utils.init_root_logger()
    utils.init_db()
    masterdata.insert_cities_masterdata()
