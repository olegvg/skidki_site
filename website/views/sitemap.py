# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, make_response, g
from commonlib.model import networks


sitemap_bp = Blueprint('sitemap', __name__)


@sitemap_bp.route('/sitemap.xml', methods=['GET'])
def sitemap():
    nets = networks.Network.objects().all()
    net_mod_dates = {}
    for net in nets:
        oldest_action = networks.NetworkAction.objects(network=net).order_by('date_from').first()
        net_mod_dates[net.name_slugified] = oldest_action.date_from

    net_actions = networks.NetworkAction.objects().all()
    cities = networks.City.objects().all()
    page = render_template('sitemap.jinja2', net_mod_dates=net_mod_dates, net_actions=net_actions, cities=cities)
    resp = make_response(page)
    resp.mimetype = 'text/xml'
    return resp