# -*- coding: utf-8 -*-


from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, make_response, g
from commonlib.model import networks, articles
from ..lib.utils import make_response_w_zero_png
from mongoengine import MultipleObjectsReturned, DoesNotExist

base_bp = Blueprint('base', __name__)


@base_bp.route('/', methods=['GET'])
def root():
    return redirect(url_for('.nets'))


@base_bp.route('/nets', methods=['GET'])
def nets():
    g.network_objs = networks.Network.objects.all()

    date_today = datetime.date(datetime.now())
    try:
        g.head_article = articles.Article.objects(
            place=u'Вводная статья',
            date_from__lte=date_today,
            date_to__gte=date_today
        ).get()
    except (MultipleObjectsReturned, DoesNotExist):
        g.head_article = None
    return render_template('networks.html')


@base_bp.route('/net/<net_name_slugified>', methods=['GET'])
def network(net_name_slugified):
    network_obj = networks.Network.objects(name_slugified=net_name_slugified).first()
    if network_obj:
        city_ids = [x.id for x in network_obj.cities]
        ordered_city_objs = networks.City.objects(id__in=city_ids).all()
        return render_template('base_network.html', network=network_obj, city_objs=ordered_city_objs)
    else:
        return render_template('no_network.html')


@base_bp.route('/cities', methods=['GET'])
def cities():
    city_objs = networks.City.objects.all()
    return render_template('cities.html', city_objs=city_objs)


@base_bp.route('/city/<city_name_slugified>', methods=['GET'])
def city_network(city_name_slugified):
    city_obj = networks.City.objects(name_slugified=city_name_slugified).first()
    if city_obj:
        network_objs = networks.Network.objects(cities=city_obj).all()
        return render_template('cities_networks.html', city=city_obj, network_objs=network_objs)
    else:
        return render_template('no_city.html')


@base_bp.route('/cat/<net_name_slugified>/<city_name_slugified>', methods=['GET'])
def catalogue(net_name_slugified, city_name_slugified):
    network_obj = networks.Network.objects(name_slugified=net_name_slugified).first()
    city_obj = networks.City.objects(name_slugified=city_name_slugified).first()
    date_today = datetime.date(datetime.now())
    if net_name_slugified == 'magnit':
        cat = networks.MagnitNetworkAction.objects(
            network=network_obj,
            cities=city_obj,
            date_from__lte=date_today,
            date_to__gte=date_today
        ).first()
        if cat:
            return render_template('cat_magnit_city.html', cat=cat, city=city_obj, network=network_obj)
    else:
        cat = networks.NetworkAction.objects(
            network=network_obj,
            cities=city_obj,
            date_from__lte=date_today,
            date_to__gte=date_today
        ).first()
        if cat:
            return render_template('cat_network_city.html', cat=cat, city=city_obj, network=network_obj)
    return render_template('no_cat.html', network=network_obj, city=city_obj)


@base_bp.route('/cat_image/<cat_oid>/<int:page>', methods=['GET'])
def cat_image(cat_oid, page):
    cat_obj = networks.NetworkAction.objects(id=cat_oid).first()
    idx = page - 1
    try:
        image_obj = cat_obj.imageset[idx]
        image = image_obj.image.read()
        content_type = image_obj.image.content_type
        resp = make_response(image)
        resp.headers['Content-Type'] = content_type
        return resp
    except (IndexError, AttributeError):
        return make_response_w_zero_png()


@base_bp.route('/magnit_cat_image/<cat_oid>/<int:cat_number>/<int:page>', methods=['GET'])
def magnit_cat_image(cat_oid, cat_number, page):
    cat_obj = networks.MagnitNetworkAction.objects(id=cat_oid).first()
    page -= 1
    cat_number -= 1
    try:
        image_obj = cat_obj.imageset_list[cat_number].imageset[page]
        image = image_obj.image.read()
        content_type = image_obj.image.content_type
        resp = make_response(image)
        resp.headers['Content-Type'] = content_type
        return resp
    except (IndexError, AttributeError):
        return make_response_w_zero_png()


@base_bp.route('/net_image/<net_name_slugified>', methods=['GET'])
def net_image(net_name_slugified):
    net_image_obj = networks.Network.objects(name_slugified=net_name_slugified).first()
    if net_image_obj:
        image = net_image_obj.image.read()
        content_type = net_image_obj.image.content_type
        resp = make_response(image)
        resp.headers['Content-Type'] = content_type
        return resp
    else:
        return make_response_w_zero_png()
