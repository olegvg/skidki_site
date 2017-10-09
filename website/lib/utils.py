# -*- coding: utf-8 -*-

import sys
import base64
from datetime import datetime
from mongoengine import connect
from flask import make_response, render_template as _render_template, url_for
from commonlib.model import analytics


def make_response_w_zero_png():
    img = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='  # 1x1.png
    resp = make_response(base64.b64decode(img))
    resp.headers['Content-Type'] = 'image/png'
    resp.status_code = 404
    return resp


def check_date_in_future(date):
    # По идее, здесь должен быть TZ-aware код, но scraper не собирает таймзоны городов и mongo не хранит их
    # по-этому нет смысла считать TZ. По дефолту, мы юзаем BABEL_DEFAULT_TIMEZONE
    delta = date - datetime.now()
    return delta.days > 0


def init_db(app):
    db = app.config['MONGODB_SETTINGS']
    db_host = db['host']
    db_port = db['port']
    db_username = db['username']
    db_password = db['password']
    db_name = db['db']
    connect(db_name, host=db_host, username=db_username, password=db_password, port=db_port, connect=False)


def fallback_blueprint_handler_maker(fallback_blueprint):
    bp_name = fallback_blueprint.name

    def url_handler(error, endpoint, values):
        if endpoint[0] == '.' or endpoint.startswith(bp_name + '.'):
            exc_type, exc_value, tb = sys.exc_info()
            if exc_value is error:
                raise exc_type, exc_value, tb
            else:
                raise error
        else:
            endpoint = endpoint.split('.')[1]
            return url_for(bp_name + '.' + endpoint, **values)
    return url_handler
