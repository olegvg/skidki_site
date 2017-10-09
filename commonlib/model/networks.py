# -*- coding: utf-8 -*-
from mongoengine import Document, EmbeddedDocument, StringField, ImageField, IntField, ListField
from mongoengine import ReferenceField, DateTimeField, EmbeddedDocumentListField


class City(Document):
    name = StringField(required=True)
    name_slugified = StringField(required=True)  # URL-slugified name (https://en.wikipedia.org/wiki/Semantic_URL#Slug)
    show_order = IntField(min_value=1, default=10000)

    meta = {
        'ordering': ['+show_order', '+name_slugified']
    }


class Network(Document):
    name = StringField(required=True)
    name_slugified = StringField(required=True)  # URL-slugified name (https://en.wikipedia.org/wiki/Semantic_URL#Slug)
    image = ImageField(required=True)
    description = StringField(required=True)
    cities = ListField(ReferenceField(City))


class OneImage(EmbeddedDocument):
    image = ImageField()


class ImagePages(Document):
    imageset = EmbeddedDocumentListField(OneImage, required=True)


class NetworkAction(Document):
    network = ReferenceField(Network, required=True)
    cities = ListField(ReferenceField(City))
    date_from = DateTimeField(required=True)
    date_to = DateTimeField(required=True)
    imageset = EmbeddedDocumentListField(OneImage)
    description = StringField()

    meta = {'allow_inheritance': True}


class MagnitNetworkAction(NetworkAction):
    imageset_list = ListField(ReferenceField(ImagePages))
