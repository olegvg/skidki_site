# -*- coding: utf-8 -*-

import sys
import logging
import os.path
import pickle
from functools import wraps
import linecache
import yaml
import mongoengine

_config = None


class NoConfigException(Exception):
    pass


def config_loader(config_file_name):
    global _config
    with open(config_file_name) as cfg_yml:
        _config = yaml.load(cfg_yml)


def get_config(fn, default=None):
    global _config
    try:
        return fn(_config)
    except (KeyError, TypeError) as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        exc_traceback = exc_traceback.tb_next

        filename = exc_traceback.tb_frame.f_code.co_filename
        lineno = exc_traceback.tb_lineno
        line = linecache.getline(filename, lineno)
        err = 'config option {} not found at File "{}", line {}, {}'.format(e, filename, lineno, line)

        logging.getLogger('scraper').error(err)

        return default


def init_root_logger():
    default_formatter = '%(asctime)s %(levelname)-8s %(name)-16s %(message)s'

    default_handler = logging.StreamHandler()
    default_formatter = logging.Formatter(default_formatter)
    default_handler.setFormatter(default_formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(default_handler)
    root_logger.setLevel(logging.DEBUG)

    root_log_format = get_config(lambda x: x['scraper']['logger']['format'], default=default_formatter)
    root_log_level = get_config(lambda x: x['scraper']['logger']['level'], default=logging.DEBUG)

    root_handler = logging.StreamHandler()
    root_formatter = logging.Formatter(root_log_format)
    root_handler.setFormatter(root_formatter)
    root_logger.removeHandler(default_handler)
    root_logger.addHandler(root_handler)
    root_logger.setLevel(root_log_level)


def init_db():
    mongo_uri = get_config(lambda x: x['scraper']['mongo']['uri'])
    username = get_config(lambda x: x['scraper']['mongo']['username'])
    password = get_config(lambda x: x['scraper']['mongo']['password'])
    mongoengine.connect(host=mongo_uri, username=username, password=password)


def pickle_if_debug(pickle_file):
    def func_decorator(f):
        @wraps(f)
        def decorator(self, *args, **kwargs):
            if self.is_debug and os.path.isfile(pickle_file):
                with open(pickle_file, 'r') as pfd:
                    return pickle.load(pfd)
            else:
                res = f(self, *args, **kwargs)
                if self.is_debug:
                    with open(pickle_file, 'w') as pfd:
                        pickle.dump(res, pfd)
                return res
        return decorator
    return func_decorator
