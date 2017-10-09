# -*- coding: utf-8 -*-
from __future__ import division

import io
import logging
from PIL import Image
from mongoengine import errors
from commonlib.model import networks
from ..lib.utils import get_config

logger = logging.getLogger('scraper').getChild(__name__)

# def cities_directory_updater(cities_url):
#     for city_url in cities_url:
#         try:
#             city_obj = networks.NetworkCity.objects(name_url=city_url).get()
#         except errors.DoesNotExist:
#             city_obj = networks.NetworkCity()
#         city_obj.name = cities_master[city_url]
#         city_obj.name_url = city_url
#         city_obj.save()


def prepare_image_fd(in_fd, out_fd, image_width, image_format='PNG', convert_params=None, save_params=None):
    logo_image = Image.open(in_fd)
    size = logo_image.getbbox()[2:]
    sample_ratio = image_width / size[0]
    new_size = map(lambda x: int(x * sample_ratio), size)
    if size[0] > image_width:    # Downsampling
        logo_image = logo_image.resize(new_size, Image.LANCZOS)
    else:                       # Upsampling
        logo_image = logo_image.resize(new_size, Image.BICUBIC)

    if convert_params is None:
        convert_params = {'mode': 'P', 'palette': 'ADAPTIVE'}
    if save_params is None:
        save_params = {'optimize': True}
    logo_image.convert(**convert_params).save(out_fd, image_format, **save_params)


def base_network_updater(scraper_name, city_names_slugified):
    logo_path = get_config(lambda x: x['scraper']['scrapers'][scraper_name]['logo_path'])
    logo_width = int(get_config(lambda x: x['scraper']['scrapers'][scraper_name]['logo_width']))
    network_name = get_config(lambda x: x['scraper']['scrapers'][scraper_name]['name'])
    network_name_slugified = get_config(lambda x: x['scraper']['scrapers'][scraper_name]['name_slugified'])
    network_descr = get_config(lambda x: x['scraper']['scrapers'][scraper_name]['description'])

    res_image_fd = io.BytesIO()
    logo_image_fd = open(logo_path)
    prepare_image_fd(logo_image_fd, res_image_fd, logo_width)

    city_objs = map(lambda x: networks.City.objects(name_slugified=x).first(), city_names_slugified)
    city_objs = filter(lambda x: x is not None, city_objs)

    try:
        network_obj = networks.Network.objects(name=network_name).get()
        network_obj.image.delete()
    except errors.DoesNotExist:
        network_obj = networks.Network()
        # Skip name and descr updating
        network_obj.name = network_name
        network_obj.name_slugified = network_name_slugified
        network_obj.description = network_descr
    network_obj.image.put(res_image_fd, content_type='image/png')
    network_obj.cities = city_objs
    network_obj.save()
    res_image_fd.close()
    logo_image_fd.close()
    return network_obj
