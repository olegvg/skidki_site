# -*- coding: utf-8 -*-

import os
import ujson
from mongoengine.connection import get_db
from mongoengine.fields import ObjectId


def insert_cities_masterdata(is_drop=True):
    db = get_db()
    cities_fname = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'masterdata', 'cities.json')
    cities_fd = open(cities_fname, 'r')
    cities = db.city
    if is_drop is True:
        cities.drop()
    for line in cities_fd:
        jsline = ujson.loads(line)
        jsline['_id'] = ObjectId(jsline['_id']['$oid'])
        print jsline
        cities.insert_one(jsline)

