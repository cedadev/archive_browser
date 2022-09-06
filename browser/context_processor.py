# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
from hashlib import sha1

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, HttpResponseRedirect
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

def data_centre(request):
    """
    Determine which data centre template is extended 
    by browse.html
    """
    
    data_centre = "fwtheme_django/layout.html" #default template
    dc_css = "browser/css/browser.css"
    for dc in settings.DATACENTRES:
        if request.path.startswith(f"/{dc}"):
            data_centre = f"browser/data_centres/{settings.DATACENTRES[dc]}"
            dc_css = f"browser/css/{dc}.css"

    context = {
        "data_centre": data_centre,
        "dc_css": dc_css
    }
    return context