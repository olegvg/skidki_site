# -*- coding: utf-8 -*-
from __future__ import division

import os.path
import io
import yaml
from PIL import Image
from mongoengine import errors
from .. import app
from commonlib.model import networks


def uploader(zf):
    with zf.open('data.yml') as data_yml:
        data = yaml.load(data_yml)

        cities_updater(data)
        networks_updater(data, zf)
        catalogues_updater(data, zf)


def cities_updater(yml):
    cities = yml['cities']
    for city in cities:
        try:
            city_obj = networks.City.objects(name=city).get()
        except errors.DoesNotExist:
            city_obj = networks.City()
        city_obj.name = city
        city_obj.name_slugified = cities[city]['translit']
        city_obj.save()


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


def networks_updater(yml, zf):
    img_dir = yml['root_images_dir']
    for network_name in yml['networks']:
        network = yml['networks'][network_name]

        res_image_fd = io.BytesIO()
        logo_image_fd = zf.open(os.path.join(img_dir, network['logo']))
        logo_width = int(app.config['UPLOADER']['network_logo_width'])
        prepare_image_fd(logo_image_fd, res_image_fd, logo_width)

        city_objs = map(lambda x: networks.City.objects(name=x).first(), network['cities'])
        city_objs = filter(lambda x: x is not None, city_objs)

        try:
            network_obj = networks.Network.objects(name=network_name).get()
            network_obj.image.delete()
        except errors.DoesNotExist:
            network_obj = networks.Network()
        network_obj.name = network_name
        network_obj.name_slugified = network['translit']
        network_obj.description = network['description']
        network_obj.image.put(res_image_fd, content_type='image/png')
        network_obj.cities = city_objs
        network_obj.save()


def catalogues_updater(yml, zf):
    catalog_page_width = int(app.config['UPLOADER']['catalog_page_width'])
    img_save_params = {
        'quality': 82,
        'optimize': True,
        'progressive': True,
        'qtables': 'web_high'
    }

    for cat in yml['catalogue']:
        network_obj = networks.Network.objects(name=cat['network']).first()

        city_objs = map(lambda x: networks.City.objects(name=x).first(), cat['cities'])
        city_objs = filter(lambda x: x is not None, city_objs)

        img_dir = os.path.join(yml['root_images_dir'], cat['pages_dir'])

        try:
            cat_obj = networks.NetworkAction.objects(
                date_from=cat['date_from'],
                date_to=cat['date_to'],
                network=network_obj
            ).get()
            cat_obj.imageset.delete()
        except errors.DoesNotExist:
            cat_obj = networks.NetworkAction()

        cat_obj.cities = city_objs
        cat_obj.date_from = cat['date_from']
        cat_obj.date_to = cat['date_to']
        cat_obj.network = network_obj

        pages_template = cat['pages_template']
        arch_images = [x for x in zf.namelist() if x.startswith(img_dir + u'/')]
        for i in xrange(1, 100):
            file_candidate = img_dir + u'/' + pages_template.format(i)
            if file_candidate in arch_images:
                res_image_fd = io.BytesIO()
                logo_image_fd = zf.open(file_candidate)
                prepare_image_fd(
                    logo_image_fd,
                    res_image_fd,
                    catalog_page_width,
                    image_format='JPEG',
                    convert_params={},
                    save_params=img_save_params
                )

                imageset = cat_obj.imageset.create()
                imageset.image.put(res_image_fd, content_type='image/jpeg')
            else:
                break
        cat_obj.save()
