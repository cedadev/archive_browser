# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render


def browse(request):
    path = request.GET.get('path')

    # Remove the trailing slash
    if path and path.endswith('/'):
        path = path[:-1]

    if path is None:
        path = "/"


    return render(request, 'browser/browse.html', {"path": path})

