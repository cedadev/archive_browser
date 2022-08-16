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
    
    data_centre = 'browser/eds.html' #default template

    for dc in settings.DATACENTRES:
        if request.path.startswith(f"/{dc}"):
            data_centre = f"browser/{settings.DATACENTRES[dc]}"

    context = {
        "data_centre": data_centre
    }
    return context