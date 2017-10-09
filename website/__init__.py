# -*- coding: utf-8 -*-

import os.path
from flask import Flask, render_template
from flask_babel import Babel
from commonlib.model import analytics
from website.lib import utils
from website.lib.utils import fallback_blueprint_handler_maker
import views


app = Flask('website')
app.config.from_json(os.path.join(os.getcwd(), 'app_config.json'))

utils.init_db(app)

babel = Babel(app)

views.register_blueprints(app)

app.jinja_options['extensions'].extend(['jinja2.ext.with_', 'jinja2.ext.loopcontrols'])
app.jinja_env.globals['check_date_in_future'] = utils.check_date_in_future

app.url_build_error_handlers.append(fallback_blueprint_handler_maker(views.base_bp))


# Setup 404 error handler
@app.errorhandler(404)
def not_found(_):
    return render_template('404.html'), 404


# Setup 500 error handler
@app.errorhandler(500)
def general_error(_):
    return render_template('500.html'), 500


# Web analytics tag source injector
@app.context_processor
def analytics_proc():
    analytic_objs = analytics.AnalyticTag.objects.all()
    if analytic_objs:
        return dict(tags=map(lambda x: x.tag, analytic_objs))

if app.debug:
    print list(app.url_map.iter_rules())

    # Disable caching of HTTP responses in debug mode. It's critical for debugging frontend / js code
    @app.after_request
    def no_cache(response):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
