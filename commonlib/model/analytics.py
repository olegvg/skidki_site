# -*- coding: utf-8 -*-

from mongoengine import Document, StringField


class AnalyticTag(Document):
    tag = StringField()
