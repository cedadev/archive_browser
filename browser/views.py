# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from hashlib import sha1
import re
from typing import DefaultDict
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from elasticsearch.exceptions import NotFoundError
import os
import yaml
import json
from ceda_elasticsearch_tools.elasticsearch import CEDAElasticsearchClient
from functools import lru_cache

def get_elasticsearch_client():
    return CEDAElasticsearchClient(timeout=30)

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


def generate_actions(ext, path, item_type, download_service):
    #print("actions")
    # Generate button for download action
    if item_type == "dir":
        return ""
 
    download_link = f"<a class='btn btn-lg' href='{download_service}{path}?download=1' title='Download file' data-toggle='tooltip'><i class='fa fa-download'></i></a>"

    # Generate button for view action
    view_link = f'<a class="btn btn-lg" href="{download_service}{path}" title="View file" data-toggle="tooltip"><i class="fa fa-eye"></i></a>'


    # Generate button for subset action
    subset_link = f"<a class='btn btn-lg' href='{download_service}/thredds/dodsC{path}.html' title='Extract subset' data-toggle='tooltip'><i class='fa fa-cogs'></i></a>"

    if ext in ("nc", ".nc", ".hdf", ".h4", ".hdf4"):
        return download_link + subset_link
    if ext in (".gif", ".jpg", ".jpeg", ".png", ".svg", ".svgz", ".wbmp", ".webp", ".ico", ".jng", ".bmp", ".txt", ".pdf", ".html"):
        return view_link + download_link
    if os.path.basename(path) == '00README':
        return view_link
    return download_link

@lru_cache(maxsize=1024)
def moles_record(path):
    import urllib.request, json 
    with urllib.request.urlopen(settings.CAT_URL + path) as url:
        data = json.loads(url.read().decode())
    return data

def moles_desc(path):
    cat_info = moles_record(path)
    if cat_info["record_type"] == "Dataset":
        return f'''<i class="fas fa-database dataset" title="These records describe and link to the actual data in our archive. 
                     They also provide spatial and temporal information, 
                     access and usage information and link to background information on why and how the data were collected." data-toggle="tooltip">
                     </i> {cat_info["title"]} 
                     <a class='pl-1' href = '{cat_info["url"]}' title = 'See catalogue entry' data-toggle='tooltip'><i class='fa fa-info-circle'></i></a>'''
    elif cat_info["record_type"] == "Dataset Collection":   
        return f'''<i class="fas fa-copy collection" title="A collection of Datasets that share some common purpose, theme or association. 
                   These collections link to one or more Dataset records." data-toggle="tooltip"></i> {cat_info["title"]} 
                   <a class='pl-1' href = '{cat_info["url"]}' title = 'See catalogue entry' data-toggle='tooltip'><i class='fa fa-info-circle'></i></a>'''
    return ""

@lru_cache(maxsize=1024)
def agg_info(path, maxtypes=5, vars_max=1000, max_ext=10):
    query = {"query": {"term": {"directory.tree": path}}, "size": 0,
             "aggs": {"size_stats":{"stats":{"field":"size"}},
                      "types": {"terms": {"field": "type", "size": maxtypes}},
                      "exts": {"terms": {"field": "ext", "size": max_ext}},
                      "vars": {"terms": {"field": "phenomena.best_name.keyword", "size": vars_max}}}}
    es = get_elasticsearch_client()
    result = es.search(index=settings.FILE_INDEX, body=query)
    result = result["aggregations"]
    total_size = result["size_stats"]["sum"]
    ave_size = result["size_stats"]["avg"]
    item_types = []
    for t in result["types"]["buckets"]:
        item_types.append((t["key"], t["doc_count"]))
    exts = []
    for e in result["exts"]["buckets"]:
        exts.append((e["key"], e["doc_count"]))      
    
    # only return vars is a short list
    vars = []
    if len(result["vars"]["buckets"]) < vars_max:
        for v in result["vars"]["buckets"]:
            vars.append(v["key"])
    else:
        vars = ["Many Variables detected..."]
    return {"total_size": total_size, "ave_size": ave_size, "item_types": item_types, "exts": exts, "vars": vars}


@csrf_exempt
def browse(request):
    path = request.path
    download_service = settings.THREDDS_SERVICE if not settings.USE_FTP else settings.FTP_SERVICE

    path = path.rstrip('/')
    if path == "": 
        path = "/"

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

    body = {
            "sort": {"name.keyword": {"order": "asc"}}, 
            "query": {"bool": {"must": [{"term": {"directory.keyword": path}}], 
                    "must_not": [{"regexp": {"name.keyword": "[.].*"}},
                                 {"exists": {"field": "removed"}}]
                    }}, "size": settings.MAX_FILES_PER_PAGE}
    print(json.dumps(body))
    result = es.search(index=settings.FILE_INDEX, body=body)
    items = [] 
    
    for hit in result["hits"]["hits"]:
        item = hit["_source"]
        if item["type"] == "file":
            item["download"] = f'{download_service}{item.get("path")}?download=1'
        if item["path"] not in settings.DO_NOT_DISPLAY:
            items.append(item)

    cat_info = moles_record(path)

    if "json" in request.GET:
        return JsonResponse({"path": path, "items": items})

    counts = DefaultDict(int)
    for item in items:
        counts[item["type"]] += 1
        item["icon"] = getIcon(item.get("type"), item.get("ext"))
        item["actions"] = generate_actions(item.get("ext"), item.get("path"), item.get("type"), download_service)

    # work out what to show in the description field
    path_desc = moles_desc(path)
    if cat_info["record_type"] != "Dataset":
        for item in items:
            item_desc = moles_desc(item.get("path"))
            if item_desc != path_desc:
                item["description"] = moles_desc(item.get("path"))       

    context = {
        "path": path,
        "items": items,
        "index_list": index_list,
        "MAX_FILES_PER_PAGE": settings.MAX_FILES_PER_PAGE,
        "messages_": messages.get_messages(request),
        "cat_info": path_desc,
        "agg_info": agg_info(path),
        "counts": counts
    }

    return render(request, 'browser/browse.html', context)


@csrf_exempt
def item_info(request):
    path = request.GET.get("p")
    print("xxxxxx")
    print(path)
    es = get_elasticsearch_client()
    try: 
        result = es.get(index=settings.FILE_INDEX, id=sha1(path.encode('utf-8')).hexdigest())
    except NotFoundError:
        return render(request, 'browser/notfound.html', {"path": path}, status=404)
    path_record = result["_source"]
    return JsonResponse(path_record)

 

def moles_cache(request):
    cache_info = moles_record.cache_info()
    if "clear" in request.GET:
        moles_record.cache_clear()
    return render(request, 'browser/moles_cache.html', {"cache_info": cache_info})

def storage_types(request):
    """
    Page to display information about different storage types
    :param request:
    :return:
    """
    return render(request, 'browser/storage_types.html')


def robots(request):
    return HttpResponseRedirect(f"/static/robots.txt")

def search(request):
    q = ''
    results = []

    if "q" in request.GET:
        q = request.GET.get("q")
        body = { 
            "query": {"match": {"name": {"query": q}}}, 
            "size": 10000}
        es = get_elasticsearch_client()
        result = es.search(index=settings.FILE_INDEX, body=body)
        for r in result["hits"]["hits"]:
            results.append(r["_source"])
        
    return render(request, 'browser/search.html', {"q": q, "results": results})
