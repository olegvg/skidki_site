# -*- coding: utf-8 -*-

import json
from datetime import datetime


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, datetime):
            return obj.strftime('%c')
        return json.JSONEncoder.default(self, obj)


def unicode_print(obj):
    print(json.dumps(obj, cls=SetEncoder, indent=4, separators=(',', ': '), ensure_ascii=False))