# -*- coding: utf-8 -*-
from mongoengine import Document, StringField, BooleanField
from mongoengine import DateTimeField


class Article(Document):
    place = StringField(required=True, choices=(u'Вводная статья',))
    is_unescaped = BooleanField()
    date_from = DateTimeField()
    date_to = DateTimeField()
    header = StringField()
    body = StringField()
