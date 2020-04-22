# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, HttpResponseRedirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json
import math
import requests
from requests.exceptions import  Timeout, ConnectionError
from django.contrib import messages
import logging
import os
from browser.utils import as_root_path, get_elasticsearch_client
import browser.queries as base_queries


class HttpResonseReadTimeout(HttpResponse):
    status_code = 408


@csrf_exempt
def browse(request):
    path = request.path

    if len(path) > 1 and path.endswith('/'):
        path = path[:-1]

    # These checks don't work against the ftp server
    if not settings.USE_FTP:

        # Check if the requested path is a file and serve
        thredds_path = f'{settings.THREDDS_SERVICE}/fileServer{path}'

        try:
            r = requests.head(thredds_path, timeout=5)

        except (Timeout, ConnectionError) as e:
            r = None
            logging.error(e)
            if '.' in os.path.basename(thredds_path):
                messages.error(request, f'Service has timed out. Try refreshing the page or click <a href="{thredds_path}">here</a> for direct download.')

        # Check if successful
        if hasattr(r, 'status_code'):
                if r.status_code in [200, 302]:
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
        "DOWNLOAD_SERVICE": settings.THREDDS_SERVICE if not settings.USE_FTP else settings.FTP_SERVICE,
        "DIRECTORY_INDEX": settings.DIRECTORY_INDEX,
        "FILE_INDEX": settings.FILE_INDEX,
        "USE_FTP": settings.USE_FTP,
        "messages_": messages.get_messages(request)
    }

    return render(request, 'browser/browse.html', context)


@as_root_path
def show_all(request, path):

    es = get_elasticsearch_client()

    results = []

    query = base_queries.file_query(path)

    query['size'] = settings.SCROLL_SIZE

    res = es.search(index="ceda-fbi", body=query)

    total_results = res["hits"]["total"]

    if total_results > 0:
        scroll_count = math.floor(total_results / settings.SCROLL_SIZE)

        hits = res["hits"]["hits"]

        results.extend(hits)
        search_after = hits[-1]["sort"]

        for search in range(scroll_count):
            query["search_after"] = search_after

            res = es.search(index="ceda-fbi", body=query)

            hits = res["hits"]["hits"]
            results.extend(hits)
            search_after = hits[-1]["sort"]

    return JsonResponse(
        {
            "results": [hit['_source'] for hit in hits],
            "result_count": total_results
        }
    )


def storage_types(request):
    """
    Page to display information about different storage types
    :param request:
    :return:
    """
    return render(request, 'browser/storage_types.html')


@as_root_path
def get_directories(request, path):
    """
    JSON endpoint to query elasticsearch directories index
    :param request:
    :return:
    """

    if path != '/' and not path.endswith('/'):
        path = f'{path}/'

    dir_query = base_queries.current_dir(path)

    if path != '/':
        dir_query['query']['bool']['must'].append({
            'prefix': {
                'path.keyword': path
            }
        })

    es = get_elasticsearch_client()
    results = es.search(index=settings.DIRECTORY_INDEX, body=dir_query)

    # Reduce the nesting for the results
    hits = [hit['_source'] for hit in results['hits']['hits']]

    # If aggregations comes back with more than 1 hit, there are > 1 MOLES records linked from this directory
    render_titles = len(results['aggregations']['descriptions']['buckets']) > 1

    return JsonResponse(
        {
            'result_count': results['hits']['total'],
            'results': hits,
            'render_titles': render_titles
        },
        json_dumps_params={'indent': 4}
    )


@as_root_path
def get_files(request, path):
    """
    JSON endpoint to query elasticsearch files index
    :param request:
    :return:
    """

    dir_query = base_queries.dir_meta(path)

    es = get_elasticsearch_client()

    results = es.search(index=settings.DIRECTORY_INDEX, body=dir_query)
    if results['hits']['total'] == 1:
        archive_path = results['hits']['hits'][0]['_source']['archive_path']

        file_query = base_queries.file_query(archive_path)

        results = es.search(index=settings.FILE_INDEX, body=file_query)
        hits = [hit['_source'] for hit in results['hits']['hits']]

        return JsonResponse(
            {
                'result_count': results['hits']['total'],
                'results': hits,
            },
            json_dumps_params={'indent': 4}
        )

    return JsonResponse({
        'result_count': 0,
        'results': [],
    })


@as_root_path
def get_collection(request, path):
    """
    Get the MOLES collection from Elasticsearch
    :param request:
    :return:
    """

    collection_query = base_queries.dir_meta(path)

    es = get_elasticsearch_client()

    results = es.search(index=settings.DIRECTORY_INDEX, body=collection_query)

    if results['hits']['total'] == 1:
        return JsonResponse({
            'results': [results['hits']['hits'][0]['_source']]
        }, json_dumps_params={'indent': 4})

    return JsonResponse({})