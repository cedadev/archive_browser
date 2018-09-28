# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render


def browse(request):
    path = request.path
    print (request.environ)

    if len(path) > 1 and path.endswith('/'):
        path = path[:-1]

    index_list = []

    if path != '/':
        split_target = path.split('/')[1:]

        for i,dir in enumerate(split_target,1):

            subset = split_target[:i]

            index_list.append(
                {
                    "path": '/'.join(subset),
                    "dir": dir
                }
            )

    return render(request, 'browser/browse.html', {"path": path, "index_list": index_list})

