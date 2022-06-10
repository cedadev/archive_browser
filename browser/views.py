# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from hashlib import sha1
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from elasticsearch.exceptions import NotFoundError
import os
from browser.utils import as_root_path, get_elasticsearch_client, pretty_print, str2bool
import browser.queries as base_queries

def getIcon(type, extension):
    if type == "dir":
        return "<span class=\"far fa-folder\"></span>"
    if type == "link":
        return "<span class=\"fas fa-link\" data-toggle=\"tooltip\" title=\"Symbolic link\"></span>"
    if extension in (".gz", ".zip", ".tar", ".tgz", ".bz2"):
        return "<span class=\"far fa-file-archive\"></span>"
    if extension in (".png", ".gif", ".tif", ".TIF"):
        return '<span class="far fa-file-image"></span>'
    if extension == "txt":
        return '<span class="far fa-file-alt"></span>'
    return '<span class="far fa-file"></span>'


def generate_actions(ext, path, download_service):
    #print("actions")
    # Generate button for download action
    download_link = f"<a class='btn btn-lg' href='{download_service}{path}?download=1' title='Download file' data-toggle='tooltip'><i class='fa fa-download'></i></a>"

    # Generate button for view action
    view_link = f'<a class="btn btn-lg" href="{download_service}{path}" title="View file" data-toggle="tooltip"><i class="fa fa-eye"></i></a>'


    # Generate button for subset action
    subset_link = f"<a class='btn btn-lg' href='{download_service}/thredds/dodsC{path}.html' title='Extract subset' data-toggle='tooltip'><i class='fa fa-cogs'></i></a>",

    if ext in (".nc", ".hdf", ".h4", ".hdf4"):
        return download_link + subset_link
    if ext in (".gif", ".jpg", ".jpeg", ".png", ".svg", ".svgz", ".wbmp", ".webp", ".ico", ".jng", ".bmp", ".txt", ".pdf", ".html"):
        return view_link + download_link
    if os.path.basename(path) == '00README':
        return view_link
    return download_link


@csrf_exempt
def browse(request):
    print("xxx")
    path = request.path
    download_service = settings.THREDDS_SERVICE if not settings.USE_FTP else settings.FTP_SERVICE

    if len(path) > 1:
        path = path.rstrip('/')

    # Check if the request is a file and redirect for direct download
    es = get_elasticsearch_client()
    try: 
        result = es.get(index=settings.FILE_INDEX, id=sha1(path.encode('utf-8')).hexdigest())
    except NotFoundError:
        return render(request, 'browser/notfound.html', {"path": path}, status=404)
    path_record = result["_source"]
    if path_record["type"] == "file": 
        return HttpResponseRedirect(f"{download_service}{path}")
    if path_record["type"] == "link":
        return HttpResponseRedirect(f'{path_record["target"]}')


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
 
    body = {"_source": {"excludes":["phenomena"]},
            "sort": {"name.keyword": {"order": "asc"}}, 
            "query": {"bool": {"must": [{"term": {"directory.keyword": path}}], 
                    "must_not": [{"regexp": {"dir.keyword": "[.].*"}}]
                    }}, "size": settings.MAX_FILES_PER_PAGE}
    result = es.search(index=settings.FILE_INDEX, body=body)
    items = [] 
    
    for hit in result["hits"]["hits"]:
        item = hit["_source"]
        item["download"] = f'{download_service}{item.get("path")}?download=1'
        items.append(item)

    if "json" in request.GET:
        return JsonResponse({"items": items})

    print(items)

    for item in items:
        item["icon"] = getIcon(item.get("type"), item.get("extension"))
        item["actions"] = generate_actions(item.get("extension"), item.get("path"), download_service)

    print(path_record)

    context = {
        "path": path,
        "items": items,
        "index_list": index_list,
        "MAX_FILES_PER_PAGE": settings.MAX_FILES_PER_PAGE,
        "messages_": messages.get_messages(request)
    }

    print(path_record)
    return render(request, 'browser/browse.html', context)


def storage_types(request):
    """
    Page to display information about different storage types
    :param request:
    :return:
    """
    return render(request, 'browser/storage_types.html')


def robots(request):
    return HttpResponseRedirect(f"/static/robots.txt")
