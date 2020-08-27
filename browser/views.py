# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, HttpResponseRedirect
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import math
import requests
from requests.exceptions import Timeout, ConnectionError
from django.contrib import messages
import logging
import os
from browser.utils import as_root_path, get_elasticsearch_client, pretty_print, str2bool
import browser.queries as base_queries
from hashlib import sha1
from elasticsearch.exceptions import NotFoundError
from django.views.generic import TemplateView

@csrf_exempt
def browse(request):
    path = request.path

    if len(path) > 1:
        path = path.rstrip('/')

    # Check if the request is a file and redirect for direct download
    es = get_elasticsearch_client()
    if es.exists(index=settings.FILE_INDEX, id=sha1(path.encode('utf-8')).hexdigest()):
        thredds_path = f'{settings.THREDDS_SERVICE}{path}'
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
        "USE_FTP": settings.USE_FTP,
        "MAX_FILES_PER_PAGE": settings.MAX_FILES_PER_PAGE,
        "messages_": messages.get_messages(request)
    }

    return render(request, 'browser/browse.html', context)


def storage_types(request):
    """
    Page to display information about different storage types
    :param request:
    :return:
    """
    return render(request, 'browser/storage_types.html')


@as_root_path
@pretty_print
def get_directories(request, path, json_params):
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
        json_dumps_params=json_params
    )


@as_root_path
@pretty_print
def get_files(request, path, json_params):
    """
    JSON endpoint to query elasticsearch files index
    :param request:
    :return:
    """

    hits = []
    first_result = {}
    total_results = 0

    id = sha1(path.encode('utf-8')).hexdigest()

    es = get_elasticsearch_client()

    try:
        results = es.get(index=settings.DIRECTORY_INDEX, id=id)
    except NotFoundError:
        results = {'found': False}

    # Check for show_all flag in query string
    show_all = str2bool(request.GET.get('show_all'))

    if results['found']:
        first_result = results['_source']
        archive_path = first_result['archive_path']

        file_query = base_queries.file_query(archive_path)

        file_results = es.search(index=settings.FILE_INDEX, body=file_query)

        total_results = file_results["hits"]["total"]

        page_hits = file_results["hits"]["hits"]
        hits.extend([hit['_source'] for hit in page_hits])

        # Scroll the results using search after
        if total_results['value'] > settings.MAX_FILES_PER_PAGE and show_all:
            if total_results['relation'] != 'eq':
                total_results = {
                    'value': es.count(index=settings.FILE_INDEX, body=file_query)['count'],
                    'relation': 'eq'
                }
            scroll_count = math.floor(total_results['value'] / settings.MAX_FILES_PER_PAGE)

            search_after = page_hits[-1]["sort"]

            for search in range(scroll_count):
                file_query["search_after"] = search_after

                file_results = es.search(index="ceda-fbi", body=file_query)

                page_hits = file_results["hits"]["hits"]
                hits.extend([hit['_source'] for hit in page_hits])
                search_after = page_hits[-1]["sort"]

    return JsonResponse(
        {
            'result_count': total_results,
            'results': hits,
            'parent_dir': first_result
        },
        json_dumps_params=json_params
    )


class RobotsTxt(TemplateView):
    template_name='browser/robots.txt'
    content_type = 'text/plain'