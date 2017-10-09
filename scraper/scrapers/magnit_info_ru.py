# -*- coding: utf-8 -*-

import logging
import re
import io
import itertools
from datetime import datetime
from lxml.html import fromstring
from gevent.pool import Pool
from ..lib.process import ScrapperBase, ThrottledRequest
from ..lib.utils import get_config, pickle_if_debug
from commonlib.model import networks
from commonlib.utils import unicode_print
from ..lib.masterdata import magnit_cities_subst
from ..lib.updater import base_network_updater, prepare_image_fd


logger = logging.getLogger('scraper').getChild(__name__)


class MagnitScraper(ScrapperBase):
    scraper_name = 'magnit_info_ru'
    request = ThrottledRequest(__name__)

    def __init__(self):
        self.base_url = get_config(lambda x: x['scraper']['scrapers'][self.scraper_name]['base_url'])
        self.is_debug = get_config(lambda x: x['scraper']['scrapers'][self.scraper_name]['debug'])
        self.catalog_page_width = int(get_config(lambda x: x['scraper']['scrapers'][self.scraper_name]['logo_width']))
        self.img_save_params = {
            'quality': 99,
            'optimize': True,
            'progressive': True,
            'qtables': 'web_high'
        }
        super(MagnitScraper, self).__init__()

    def run(self):
        page = self.request('get', self.base_url)
        regions_e = fromstring(page.content).cssselect('.index_tabs > *')

        cities_db = {x.name: x for x in networks.City.objects().all()}
        sel_cities = []
        for region_e in regions_e:
            region_site_id = re.search('(\d+)', region_e.attrib['id']).group(1)
            cities_e = region_e.cssselect('.region_div > a')
            for city_e in cities_e:
                city_name = city_e.text
                city_site_id = re.search('(\d+)', city_e.attrib['href']).group(1)
                try:
                    city_name = magnit_cities_subst[city_name]
                except KeyError:
                    pass
                if city_name in cities_db.keys():
                    sel_cities.append([city_name, region_site_id, city_site_id])

        intersect_cities = networks.City.objects(name__nin=[x[0] for x in sel_cities]).all()
        if len(intersect_cities):
            intersect_cities_text = u', '.join([x.name for x in intersect_cities])
            logger.info(u'Cities in collection \'city\' which are not updated: {}'.format(intersect_cities_text))

        catalogs = self.get_cities_info(sel_cities)
        # catalog entry is '[catalog_id, city_name, start_date, end_date]'

        term_by_catalog = {}
        for cat in catalogs:
            term_by_catalog[cat[0]] = cat[2:4]
        # unicode_print(term_by_catalog)

        joined_by_city_catalogs = {}
        for cat in catalogs:
            city_id = cat[1]
            if city_id not in joined_by_city_catalogs:
                joined_by_city_catalogs[city_id] = []
            joined_by_city_catalogs[city_id].append(cat[0])
        # unicode_print(joined_by_city_catalogs)

        joined_by_catid_catalogs = {}
        for cat in catalogs:
            catalog_id = cat[0]
            if catalog_id not in joined_by_catid_catalogs:
                joined_by_catid_catalogs[catalog_id] = []
            joined_by_catid_catalogs[catalog_id].append(cat[1])
        # unicode_print(joined_by_catid_catalogs)

        catalog_pages = self.create_catalog_entries(joined_by_catid_catalogs.keys())

        joined_cities = []
        for i, city in enumerate(joined_by_city_catalogs):
            joined_cities.append([set(), []])
            joined_cities[i][0].add(city)
            for cat_id in joined_by_city_catalogs[city]:
                for rest_city in joined_by_catid_catalogs[cat_id]:
                    joined_cities[i][0].add(rest_city)
            joined_cities[i][1].extend(joined_by_city_catalogs[city])
        # unicode_print(joined_cities)

        city_names_slugified = [cities_db[x].name_slugified for x in joined_by_city_catalogs]
        network_obj = base_network_updater(self.scraper_name, city_names_slugified)

        for action in joined_cities:
            cities, cat_ids = action
            cat_terms = [term_by_catalog[x] for x in cat_ids]
            terms_rot = zip(*cat_terms)
            start_date = min(terms_rot[0])
            end_date = max(terms_rot[1])

            network_action_objs = networks.MagnitNetworkAction.objects(
                network=network_obj,
                date_from=start_date,
                date_to=end_date).all()
            for network_action_obj in network_action_objs:
                for old_image_page in network_action_obj.imageset_list:
                    old_image_page.imageset.delete()

            network_action_obj = networks.MagnitNetworkAction(
                network=network_obj,
                cities=[cities_db[x] for x in cities],
                date_from=start_date,
                date_to=end_date,
                imageset_list=[catalog_pages[x] for x in cat_ids if x in catalog_pages]
            )
            network_action_obj.save()

    @pickle_if_debug('../tmp/magnit_catalogs.pickle')
    def get_cities_info(self, cities):
        catalogs = Pool().imap_unordered(self.get_city_info, cities)
        return [x for x in itertools.chain.from_iterable(catalogs)]

    def get_city_info(self, city_data):
        city_name, region_site_id, city_site_id = city_data
        cookies = {'BITRIX_SM_myreg': region_site_id, 'BITRIX_SM_mycity': city_site_id}
        page = self.request('get', self.base_url, cookies=cookies)
        magazine_roots_e = fromstring(page.text).cssselect('div.magazine')
        catalogs = []
        for magazine_root_e in magazine_roots_e:
            magazine_link_e = magazine_root_e.cssselect('a.fancybox-iframe')[0]
            if magazine_link_e.text == u'Журнал магазинов Магнит':
                catalog_id = int(re.search('(\d+)/.+', magazine_link_e.attrib['href']).group(1))

                magazine_dates = magazine_root_e.cssselect('div.b-date')[0].text
                start, end = magazine_dates.split('-')
                start = start.split('.')
                end = end.split('.')
                today = datetime.today()
                start_date = datetime(day=int(start[0]), month=int(start[1]), year=today.year)
                end_date = datetime(day=int(end[0]), month=int(end[1]), year=today.year)
                catalogs.append([catalog_id, city_name, start_date, end_date])
        return catalogs

    @pickle_if_debug('../tmp/magnit_catalogs_properties.pickle')
    def create_catalog_entries(self, catalogs):
        catalog_entries = Pool().imap_unordered(self.create_catalog_entry, catalogs)
        flatten_entries = itertools.chain.from_iterable(catalog_entries)
        flatten_entries_iter = itertools.ifilter(None, flatten_entries)

        # make dict from flat list of pairs (catalog_site_id, ImagePages())
        return dict(zip(flatten_entries_iter, flatten_entries_iter))

    def create_catalog_entry(self, catalog_site_id):
        properties_url = 'http://magnit-info.ru/buyers/magazines/{}' \
                         '/files/assets/mobile/properties.js'.format(catalog_site_id)
        properties = self.request('get', properties_url).text

        if len(properties) == 0:
            logger.info('Properties file \'{}\' has a zero size'.format(properties_url))
            return [None, None]
        pagecount = int(re.search('"pageCount":(\d+)', properties).group(1))
        img_urls = ['http://magnit-info.ru/buyers/magazines/{}/files/assets/mobile/pages/'
                    'page{:04d}_i2.jpg'.format(catalog_site_id, x) for x in xrange(1, pagecount+1)]
        images = Pool().map(lambda x: self.request('get', x).content, img_urls)

        image_pages = networks.ImagePages()
        for img in images:
            res_image_fd = io.BytesIO()
            page_image_fd = io.BytesIO(img)
            prepare_image_fd(
                page_image_fd,
                res_image_fd,
                self.catalog_page_width,
                image_format='JPEG',
                convert_params={},
                save_params=self.img_save_params
            )
            imageset = image_pages.imageset.create()
            imageset.image.put(res_image_fd, content_type='image/jpeg')
        image_pages.save()
        return catalog_site_id, image_pages
