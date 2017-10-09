# -*- coding: utf-8 -*-

import os
from flask import Flask, current_app as app
from flask_mongoengine import MongoEngine
from commonlib.model import analytics

_app = Flask('website')

with _app.app_context():
    app.config.from_json(os.path.join(os.getcwd(), 'app_config.json'))
    db = MongoEngine(app)

    tag = analytics.AnalyticTag(
        tag="<script> \
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){ \
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o), \
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m) \
  })(window,document,'script','https://www.google-analytics.com/analytics.js','ga'); \
\
  ga('create', 'UA-81489044-1', 'auto'); \
  ga('send', 'pageview'); \
\
</script>"
    )

    tag.save()
