# -*- coding: utf-8 -*-


from base import base_bp
from sitemap import sitemap_bp


def register_blueprints(app):
    app.register_blueprint(base_bp)
    app.register_blueprint(sitemap_bp, url_prefix='/iA2VMsQj46k')   # чтобы враги не догадались где sitemap.xml :)
