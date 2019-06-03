# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, HttpResponse, HttpResponseRedirect
from django.http import HttpResponseNotFound, HttpResponse
from archive_browser.settings import THREDDS_SERVICE, DIRECTORY_INDEX, FILE_INDEX
from django.views.decorators.csrf import csrf_exempt
from elasticsearch import Elasticsearch
import json
import math
import requests
from requests.exceptions import  Timeout, ConnectionError
from django.contrib import messages
import logging

class HttpResonseReadTimeout(HttpResponse):
    status_code = 408

@csrf_exempt
def browse(request):
    path = request.path

    if len(path) > 1 and path.endswith('/'):
        path = path[:-1]

    # Check if the requested path is a file and serve
    thredds_path = f'{THREDDS_SERVICE}/fileServer{path}'

    try:
        r = requests.head(thredds_path, timeout=5)

    except (Timeout, ConnectionError) as e:
        r = None
        logging.error(e)
        messages.error(request, 'We are experiencing problems contacting the download server. '
                                'Viewing or downloading files may not be possible until the issue is resolved.')

    # Check if successful
    if hasattr(r, 'status_code'):
            if r.status_code in [200, 302]:
                return HttpResponseRedirect(thredds_path)

    # Check if the requested directory path is real. Ignore top level directories
    # to reduce response time.
    if path not in ['/','/badc','/neodc','/ngdc']:
        thredds_path = f'{THREDDS_SERVICE}/catalog{path}/catalog.html'

        # Set timeout to stop data.ceda from hanging when dap.ceda takes a while to respond.
        # 404s are usually quick so can continue after 0.5 seconds.
        try:
            r = requests.head(thredds_path, timeout=0.5)

        except Timeout as e:
            logging.error(e)

        # If directory is not in the archive, give a response
        if hasattr(r, 'status_code'):
            if r.status_code == 404:
                return  HttpResponseNotFound("Resource not found in the CEDA archive")

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
        "FILE_INDEX": FILE_INDEX,
        "messages_": messages.get_messages(request)
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
