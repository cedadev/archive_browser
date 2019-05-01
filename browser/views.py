# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, HttpResponse, HttpResponseRedirect
from archive_browser.settings import THREDDS_SERVICE, DIRECTORY_INDEX, FILE_INDEX
from django.views.decorators.csrf import csrf_exempt
from elasticsearch import Elasticsearch
import json
import math
import requests


@csrf_exempt
def browse(request):
    path = request.path

    if len(path) > 1 and path.endswith('/'):
        path = path[:-1]

    # Check if the requested path is a file and serve
    thredds_path = f'{THREDDS_SERVICE}/fileServer{path}'

    r = requests.head(thredds_path)
    if r.status_code == 200:
        return HttpResponseRedirect(thredds_path)

    index_list = []

    if path != '/':
        split_target = path.split('/')[1:]

        for i, dir in enumerate(split_target, 1):
            subset = split_target[:i]

            index_list.append(
                {
                    "path": '/'.join(subset),
                    "dir": dir,
                }
            )

    context = {
        "path": path,
        "index_list": index_list,
        "THREDDS_SERVICE": THREDDS_SERVICE,
        "DIRECTORY_INDEX": DIRECTORY_INDEX,
        "FILE_INDEX": FILE_INDEX
    }

    return render(request, 'browser/browse.html', context)


def show_all(request, path):
    scroll_size = 10000

    es = Elasticsearch(hosts=["https://jasmin-es1.ceda.ac.uk"])

    results = []

    query = {"query": {
        "term": {
            "info.directory": "/{}".format(path)
        }
    },
        "sort": {
            "info.name": {
                "order": "asc"
            }
        },
        "size": scroll_size
    }

    res = es.search(index="ceda-fbi", body=query)

    total_results = res["hits"]["total"]

    if total_results > 0:
        scroll_count = math.floor(total_results / scroll_size)

        hits = res["hits"]["hits"]

        results.extend(hits)
        search_after = hits[-1]["sort"]

        for search in range(scroll_count):
            query["search_after"] = search_after

            res = es.search(index="ceda-fbi", body=query)

            hits = res["hits"]["hits"]
            results.extend(hits)
            search_after = hits[-1]["sort"]

    return HttpResponse(json.dumps({"results": results}), content_type="application/json")
