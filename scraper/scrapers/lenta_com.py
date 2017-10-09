# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import re
import io
from datetime import datetime
import itertools
from lxml.html import fromstring
import ujson
from gevent.pool import Pool
import transliterate
from ..lib.process import ScrapperBase, ThrottledRequest
from ..lib.utils import get_config, pickle_if_debug
from commonlib.model import networks
from ..lib.masterdata import lenta_cities_master
from ..lib.updater import base_network_updater, prepare_image_fd


logger = logging.getLogger('scraper').getChild(__name__)


class LentaScraper(ScrapperBase):
    scraper_name = 'lenta_com'
    request = ThrottledRequest(__name__)
    network_obj = None

    def run(self):
        base_url = get_config(lambda x: x['scraper']['scrapers'][self.scraper_name]['base_url'])
        page = self.request('get', base_url).content
        regions = set(re.findall('(http://www\.(?!slideshow).+?\.lenta\.com)', page))
        regions_cat = [x+'/elektronnyy-katalog/' for x in regions]

        main_pool = Pool()
        catalog_urls = main_pool.map(self.get_catalog_urls, regions_cat)
        catalog_urls = [x for x in catalog_urls if x]
        net_actions = main_pool.map(self.get_action_info, catalog_urls)
        net_actions = [x for x in net_actions if x]

        nested_cities_slugified = [x[0] for x in net_actions if x]
        city_names_slugified = set(itertools.chain.from_iterable(nested_cities_slugified))

        self.network_obj = base_network_updater(self.scraper_name, city_names_slugified)

        self.drop_old_net_actions(net_actions)
        main_pool.map(self.update_net_action, net_actions)

        # validation of intersection between Lenta's masterdata and mongodb's City entries
        intersect_cities = networks.City.objects(name_slugified__nin=city_names_slugified).all()
        if len(intersect_cities):
            intersect_cities_text = ', '.join([x.name for x in intersect_cities])
            logger.error(u'Cities in collection \'city\' which are not updated: {}'.format(intersect_cities_text))

    def get_catalog_urls(self, url):
        page = self.request('get', url).content
        page_e = fromstring(page)
        href = page_e.cssselect('#js-canvas > div > div > section > '
                                'div > div > main > div.el-catalog-list > '
                                'div > div > a > b')
        for b in href:
            if b.text_content() == u'Каталог':
                rt = re.search('\'(.+?)\'', b.getparent().attrib['href']).group(1)
                return rt

    @pickle_if_debug('../tmp/magnit_catalogs.pickle')
    def get_action_info(self, url):
        page = self.request('get', url).content
        try:
            part_json_url = re.search('\'\.(/xml/pagedata_.+?\.json)\'', page).group(1)
        except AttributeError:
            return None
        json_url = 'http://www.slideshow.lenta.com/' + part_json_url
        json = self.request('get', json_url).content
        catalog = ujson.loads(json)
        page_urls_dict = {int(x['name']): x['big'] for x in catalog['images']}

        cities = catalog['name'].split(u'. ')
        date_from = datetime.strptime(catalog['date_start'], '%Y-%m-%d')
        date_to = datetime.strptime(catalog['date_end'], '%Y-%m-%d')

        cities_slugified = []
        for x in cities:
            trlit = re.sub('\'', '', transliterate.translit(x.lower(), reversed=True))
            trlit = re.sub('\s', '-', trlit)
            cities_slugified.append(trlit)

        valid_cities_slugified = [x for x in cities_slugified if x in lenta_cities_master]
        if len(valid_cities_slugified):
            return valid_cities_slugified, date_from, date_to, page_urls_dict
        else:
            return None

    def drop_old_net_actions(self, actions):
        old_cat_objs = []
        for action in actions:
            _, date_from, date_to, _ = action
            old_cat_objs.extend(networks.NetworkAction.objects(
                date_from=date_from,
                date_to=date_to,
                network=self.network_obj
            ))
        for old_cat_obj in old_cat_objs:
            old_cat_obj.imageset.delete()
            old_cat_obj.delete()

    def update_net_action(self, action):
        cities_slugified, date_from, date_to, pages = action

        catalog_page_width = int(get_config(lambda x: x['scraper']['scrapers'][self.scraper_name]['logo_width']))
        img_save_params = {
            'quality': 99,
            'optimize': True,
            'progressive': True,
            'qtables': 'web_high'
        }

        city_objs = map(lambda x: networks.City.objects(name_slugified=x).first(), cities_slugified)
        city_objs = filter(lambda x: x is not None, city_objs)

        cat_obj = networks.NetworkAction()

        cat_obj.cities = city_objs
        cat_obj.date_from = date_from
        cat_obj.date_to = date_to
        cat_obj.network = self.network_obj

        for i in sorted(pages.keys()):
            res_image_fd = io.BytesIO()
            page_url = 'http://www.slideshow.lenta.com/' + pages[i]
            page_image = self.request('get', page_url).content
            page_image_fd = io.BytesIO(page_image)
            prepare_image_fd(
                page_image_fd,
                res_image_fd,
                catalog_page_width,
                image_format='JPEG',
                convert_params={},
                save_params=img_save_params
            )

            imageset = cat_obj.imageset.create()
            imageset.image.put(res_image_fd, content_type='image/jpeg')
        cat_obj.save()
