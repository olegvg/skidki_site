# -*- coding: utf-8 -*-

import abc
import logging
import gevent
from gevent.lock import BoundedSemaphore
from gevent import monkey
monkey.patch_all()
from .utils import get_config
import requests


class AbstractSingletonMeta(abc.ABCMeta):
    # noinspection PyArgumentList
    def __call__(cls, *args, **kwargs):
        key = 'inst_' + str(hash(tuple(args + tuple(sorted(kwargs.items())))))
        if getattr(cls, key, None) is None:
            logging.getLogger('scraper').debug(
                'Create a new singleton {} with args: {}, {}'.format(cls.__name__, args, kwargs)
            )
            new_inst = super(AbstractSingletonMeta, cls).__call__(*args, **kwargs)
            setattr(cls, key, new_inst)
        return getattr(cls, key)


class ThrottledRequest(object):
    __metaclass__ = AbstractSingletonMeta

    def __init__(self, instance_name=None):
        # instance name is used by SingletonMeta as discriminator at the moment of singleton instance creation
        self.instance_name = instance_name

        sim_reqs = get_config(lambda x: x['scraper']['simultaneous_requests'], 5)
        self.semaphore = BoundedSemaphore(sim_reqs)

        self.args = {}

        try:
            proxies_param = get_config(lambda x: x['scraper']['proxies'])
            proxies = {}
            for proxy in proxies_param:
                proxy_split = proxy.split(':')
                proxy = {proxy_split[0]: proxy}
                proxies.update(proxy)
            self.args['proxies'] = proxies
        except (IndexError, TypeError):
            logging.getLogger('scraper').warn("'config:scraper.proxies' not found, going on without proxies")

        custom_headers = get_config(lambda x: x['scraper']['custom_headers'])
        self.args['headers'] = custom_headers
        self.session = requests.Session()

    def __call__(self, *args, **kwargs):
        with self.semaphore:
            kwargs.update(self.args)
            resp = self.session.request(*args, **kwargs)
        return resp


class ScrapperBase(object):
    __metaclass__ = abc.ABCMeta
    is_debug = False

    def async_run(self):
        return gevent.spawn(self.run)

    @abc.abstractmethod
    def run(self):
        pass
