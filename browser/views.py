# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from hashlib import sha1
from typing import DefaultDict
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from .lru_cache_expires import lru_cache_expires
import os
import urllib.request
import urllib.error
import json 
from functools import lru_cache 
from fbi_core import archive_summary, fbi_listdir, get_record, ls_query
from elasticsearch.helpers import ScanError


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
    # Generate button for download action
    if item_type in ("dir", "link"):
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

@lru_cache_expires(maxsize=2048, max_expire_period=2*3600, default=None)
def get_access_rules(path):
    if path == "/": 
        return []
    url = settings.ACCESSCTL_URL + path
    with urllib.request.urlopen(settings.ACCESSCTL_URL + path) as page:
        data = json.loads(page.read().decode())
    shortest = "x" * 1000    
    for key in data:
        if len(key) < len(shortest):
            shortest = key 
    return data[shortest]

@lru_cache(maxsize=2048)
def moles_record(path):
    for CAT_URL in settings.CAT_URLS:
        try:
            with urllib.request.urlopen(CAT_URL + path) as url:
                data = json.loads(url.read().decode())
            return data
        except (ConnectionResetError, urllib.error.HTTPError):
            continue
    return None

def readme_line(path):
    """get readme line"""
    readme_file = os.path.join(path, "00README") 
    readme_record = get_record(readme_file)
    if readme_record is None:
        return None
    if "content" in readme_record: 
        first_chars = readme_record["content"][:500]
        return first_chars.splitlines()[0]
    else:
        return None
 
@lru_cache_expires(maxsize=2048, max_expire_period=2*3600, default=None)
def directory_desc(path):
    cat_info = moles_record(path)
    if cat_info is not None and cat_info["record_type"] == "Dataset":
        return f'''<i class="fas fa-database dataset" title="These records describe and link to the actual data in our archive. 
                     They also provide spatial and temporal information, 
                     access and usage information and link to background information on why and how the data were collected." data-toggle="tooltip">
                     </i> {cat_info["title"]} 
                     <a class='pl-1' href = '{cat_info["url"]}' title = 'See catalogue entry' data-toggle='tooltip'><i class='fa fa-info-circle'></i></a>'''
    elif cat_info is not None and cat_info["record_type"] == "Dataset Collection":   
        return f'''<i class="fas fa-copy collection" title="A collection of Datasets that share some common purpose, theme or association. 
                   " data-toggle="tooltip"></i> {cat_info["title"]} 
                   <a class='pl-1' href = '{cat_info["url"]}' title = 'See catalogue entry' data-toggle='tooltip'><i class='fa fa-info-circle'></i></a>'''
    readme_info = readme_line(path)
    if readme_info:
        return f'<i class="fab fa-readme" title="" data-toggle="tooltip" data-original-title="Description taken from 00README"></i> {readme_info}' 
    return ""

@lru_cache_expires(maxsize=1024, max_expire_period=10*3600, default=None)   #, min_call_time_for_caching=1.0, run_based_expire_factor=1000)
def agg_info(path, maxtypes=5, vars_max=1000, max_ext=10):
    summary = archive_summary(path, max_types=maxtypes, max_vars=vars_max, max_exts=max_ext)
    total_size = summary["size_stats"]["sum"]
    ave_size = summary["size_stats"]["avg"]
    item_types = summary["types"]
    exts = summary["exts"]
      
    # only return vars is a short list
    vars = []
    if len(summary["vars"]) < vars_max:
        for v in summary["vars"]:
            vars.append(v[0])
    else:
        vars = ["Many Variables detected..."]
    return {"total_size": total_size, "ave_size": ave_size, "item_types": item_types, "exts": exts, "vars": vars}


def make_breadcrumbs(path):
    index_list = [{"path": "", "dir": "archive"}]
    if path == "/":
        return index_list

    split_target = path.split('/')[1:]
    for i, dir in enumerate(split_target, 1):
        subset = split_target[:i]
        index_list.append({"path": '/'.join(subset), "dir": dir}) 
    return index_list   

def browse_query(path, show_hidden, show_removed):
    body = {
            "sort": {"name.keyword": {"order": "asc"}}, 
            "query": {"bool": {"must": [{"term": {"directory.keyword": path}}], 
                    "must_not": []
                    }}, "size": settings.MAX_FILES_PER_PAGE}
    
    if not show_removed:
        body["query"]["bool"]["must_not"].append({"exists": {"field": "removed"}})
    if not show_hidden:
        body["query"]["bool"]["must_not"].append({"regexp": {"name.keyword": "[.].*"}})    
    return body

@csrf_exempt
def browse(request):
    path = request.path
    download_service = settings.THREDDS_SERVICE if not settings.USE_FTP else settings.FTP_SERVICE

    path = path.rstrip('/')
    if path == "": 
        path = "/"

    # Check if the request is a file and redirect for direct download
    path_record = get_record(path)
    print(path_record)
    if path_record is None:
        return render(request, 'browser/notfound.html', {"path": path}, status=404)
    if path_record["type"] == "file": 
        return HttpResponseRedirect(f"{download_service}{path}")
    if path_record["type"] == "link":
        return HttpResponseRedirect(f'{path_record["target"]}')

    index_list = make_breadcrumbs(path)
    show_hidden = "hidden" in request.GET
    show_removed = "removed" in request.GET
    if show_removed: show_hidden = True
    
    items = []
    try:
        for item in fbi_listdir(path, removed=show_removed, hidden=show_hidden):
            if item["type"] == "file":
                item["download"] = f'{download_service}{item.get("path")}?download=1'
            if item["path"] not in settings.DO_NOT_DISPLAY:
                items.append(item)
    except ScanError: 
        return HttpResponseRedirect(f"{download_service}{path}/")

    cat_info = moles_record(path)

    if "json" in request.GET:
        return JsonResponse({"path": path, "items": items})

    access_rules = get_access_rules(path)

    counts = DefaultDict(int)
    for item in items:
        counts[item["type"]] += 1
        item["icon"] = getIcon(item.get("type"), item.get("ext"))
        item["actions"] = generate_actions(item.get("ext"), item.get("path"), item.get("type"), download_service)

    # work out what to show in the description field
    path_desc = directory_desc(path)
    refresh = False
    if cat_info is not None and cat_info["record_type"] != "Dataset":
        for item in items:
            item_desc = ''
            if item["type"] == "dir":
                item_desc = directory_desc(item.get("path"))
                if item_desc is None:
                    item_desc = '' # '<img src="/staticfiles/browser/img/bodc.png" width="25" >' # loading.gif
                    refresh = True
                if item_desc != path_desc:
                    item["description"] = item_desc
 
    summary = agg_info(path)
    if summary is None: 
        refresh = True

    template = 'browser/browse_base.html'
    if show_removed:
        template = 'browser/browse_removed.html'
        messages.warning(request, f'Viewing removed and hidden files. <a href="{path}">Normal view</a>')
    elif show_hidden:
        template = 'browser/browse_hidden.html'
        messages.info(request, f'Viewing hidden files. <a href="{path}">Normal view</a>')

    context = {
        "path": path,
        "items": items,
        "index_list": index_list,
        "MAX_FILES_PER_PAGE": settings.MAX_FILES_PER_PAGE,
        "messages_": messages.get_messages(request),
        "cat_info": path_desc,
        "agg_info": summary,
        "counts": counts,
        "refresh": refresh,
        "access_rules": access_rules,
        "DOWNLOAD_SERVICE": download_service
    }
 
    return render(request, template, context)


@csrf_exempt
def item_info(request):
    path = request.GET.get("p")
    path_record = get_record(path)
    if path_record is None:
        render(request, 'browser/notfound.html', {"path": path}, status=404)
    return JsonResponse(path_record)


def cache_control(request):
    context = {"directory_desc": directory_desc.cache_info(), 
               "agg": agg_info.cache_info()}
    if "clear_all" in request.GET:
        directory_desc.cache_clear()
    if "clear" in request.GET:
        path = request.GET.get("clear")
        directory_desc.cache_clear_key(path)
        agg_info.cache_clear_key(path)
    return render(request, 'browser/cache.html', context)

def storage_types(request):
    """
    Page to display information about different storage types
    :param request:
    :return:
    """
    return render(request, 'browser/storage_types.html')


def robots(request):
    return HttpResponseRedirect(f"/staticfiles/robots.txt")

def search(request):
    q = ''
    files = []
    if "under" in request.GET:
        under = request.GET.get("under")
    else: 
        under="/"

    if "q" in request.GET:
        q = request.GET.get("q")
        files = ls_query(under, name_regex=q)
    return render(request, 'browser/search.html', {"q": q, "results": files})

    
