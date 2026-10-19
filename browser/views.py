# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import fnmatch
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
from fbi_core import archive_summary, fbi_listdir, get_record, ls_query, es, indexname
from elasticsearch.helpers import ScanError
from .catalogue_cache import observation_cache

obs_cache, collections_cache, projects_cache = observation_cache()



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
    #
    # Make sure uppercase extensions are handled as well
    
    if ext:
        ext = ext.lower()
    
    if item_type in ("dir", "link"):
        return ""
 
    # Generate button for view action
    view_link = f'<a class="btn" href="{download_service}{path}" title="View file" data-toggle="tooltip"><i class="fa fa-eye"></i> View</a>'

    # Generate button for subset action
    subset_link = f"""<a class='btn' href='{download_service}/thredds/dodsC{path}.html' 
                    title='Extract subset' data-toggle='tooltip'><i class='fa fa-cogs'></i> Subset</a>"""

    if ext in ("nc", ".nc", ".hdf", ".h4", ".hdf4"):
        return subset_link
    if ext in (".gif", ".jpg", ".jpeg", ".png", ".svg", ".svgz", ".wbmp", ".webp", ".ico", ".jng", ".bmp", ".txt", ".pdf", ".html", ".mp4"):
        return view_link
    if os.path.basename(path) == '00README':
        return view_link
    return ""

@lru_cache_expires(maxsize=16384, max_expire_period=2*3600, default=None)
def get_access_rules(path):
    if path == "/": 
        return []
    url = settings.ACCESSCTL_URL + path
    #print(url)
    with urllib.request.urlopen(settings.ACCESSCTL_URL + path) as page:
        data = json.loads(page.read().decode())
    shortest = "x" * 1000    
    for key in data:
        if len(key) < len(shortest):
            shortest = key 
    print(f"👾 get_access_rules for {path}: {data[shortest]}")
    if data[shortest] == "no matching paths":
        return []
    else:
        return data[shortest]

@lru_cache(maxsize=16384)
def readme_line(path):
    """get readme line"""
    print(f"🐔", end='')
    for readme_filename in ("00README.txt", "00README"):
        readme_file = os.path.join(path, readme_filename)
        readme_record = get_record(readme_file)
        if readme_record is not None:
            break
    else:
        return None

    if "content" in readme_record: 
        first_chars = readme_record["content"][:500]
        if first_chars:
            return first_chars.splitlines()[0]
    else:
        return None

def cat_button(cat_info, cat_type):
    cat_url = f'https://catalogue.ceda.ac.uk/uuid/{cat_info["uuid"]}'
    if cat_type == "observation":
        if cat_info["status"] in ('superseded', 'obsolete', 'historicalArchive', 'retired', 'deprecated'):
            status_badge = f'<span class="badge badge-danger">{cat_info["status"]}</span>'
            button_type = "btn-outline-warning"
        else:
            status_badge = ""
            button_type = "btn-outline-primary"
        if cat_info["publicationState"] in ('working', 'preview'):
            publication_badge = f'<span class="badge badge-warning">{cat_info["publicationState"]}</span>'
        else:
            publication_badge = ""  
        return f'''<a href="{cat_url}" class="btn {button_type} btn-sm">
                     <i class="fa-lg fa fa-database" style="color: #4f81bd" title="Dataset information" data-toggle="tooltip"></i> 
                     Dataset {status_badge} {publication_badge}</a> {cat_info["title"]}'''
    elif cat_type == "collection":
        return f'''<a href="{cat_url}" class="btn btn-outline-primary btn-sm">
                   <i class="fas fa-copy collection" style="color: #4807b3" title="A collection of Datasets." data-toggle="tooltip"></i> Collection</a> 
                   {cat_info["title"]}'''    
    elif cat_type == "project":
        return f'''<a href="{cat_url}" class="btn btn-outline-primary btn-sm">
                   <i class="fas fa-users project" style="color: #ea3838" title="A project." data-toggle="tooltip"></i> Project</a>
                   {cat_info["title"]}'''


def directory_desc(path, item_type=None, mod_time=None):
    if item_type == "file":
        return f"{mod_time}"

    cat_info = obs_cache[path]
    if cat_info is not None:
        cat_type = "observation"
    else:
        cat_info = collections_cache.get(path)
        if cat_info is not None:
            cat_type = "collection"
        else:
            cat_info = projects_cache.get(path)
            if cat_info is not None:
                cat_type = "project"
            else:
                cat_type = None

    # if there is no catalogue info, check for a readme file
    if cat_info is None:
        readme_info = readme_line(path)
        if readme_info and readme_info != 'HIDE DIRECTORY':
            return f'{readme_info}' 
        else:
            return ""

    #print(f"collections_cache: {collections_cache}")
    return f"{cat_button(cat_info, cat_type)} {cat_info['title']}"


@lru_cache_expires(maxsize=16384, max_expire_period=10*3600, default=None)   #, min_call_time_for_caching=1.0, run_based_expire_factor=1000)
def agg_info(path, maxtypes=5, vars_max=1000, max_ext=10):
    print(f"🐸", end='')
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

    nfiles = 0
    for item_type, number in item_types:
        if item_type == "file":
            nfiles = number

    summary = archive_summary(path, max_types=maxtypes, max_vars=vars_max, 
                              max_exts=max_ext, location="on_tape")
    tape_total_size = summary["size_stats"]["sum"]
    return {"total_size": total_size, "ave_size": ave_size, "item_types": item_types, "exts": exts, 
            "vars": vars, "tape_size": tape_total_size, "nfiles": nfiles}


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
    # print(path_record)
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
            if item["type"] == "dir" and agg_info(item.get("path")):
                item["agg_info"] = agg_info(item.get("path"))
            if item["path"] not in settings.DO_NOT_DISPLAY:
                items.append(item)
    except ScanError: 
        return HttpResponseRedirect(f"{download_service}{path}/")

    cat_info = obs_cache[path]
    if cat_info is None:
        cat_info = collections_cache.get(path)
    if cat_info is None:
        cat_info = projects_cache.get(path)

    if "json" in request.GET:
        return JsonResponse({"path": path, "items": items})

    access_rules = get_access_rules(path)
    print(f"🤖 access_rules for {path}: {access_rules}")

    counts = DefaultDict(int)
    for item in items:
        counts[item["type"]] += 1
        item["icon"] = getIcon(item.get("type"), item.get("ext"))
        item["on_tape"] = item.get("location") == ["on_tape"]
        item["actions"] = generate_actions(item.get("ext"), item.get("path"), item.get("type"), download_service)

    # work out what to show in the description field
    path_desc = directory_desc(path, item_type="dir")
    refresh = False
    print(f"cat_info: {cat_info}")
    
    for item in items:
        item_desc = directory_desc(item.get("path"), item.get("type"), mod_time=item.get("last_modified"))
        if item_desc != path_desc:
            item["description"] = item_desc

    summary = agg_info(path)
    #if summary is None:
    #    refresh = True

    template = 'browser/browse_base.html'
    if show_removed:
        template = 'browser/browse_removed.html'
        messages.warning(request, f'Viewing removed and hidden files. <a href="{path}">Normal view</a>')
    elif show_hidden:
        template = 'browser/browse_hidden.html'
        messages.info(request, f'Viewing hidden files. <a href="{path}">Normal view</a>')

    status = 200
    if "forbidden" in request.GET:
        messages.error(request, f'''You don't have permission to access files in this directory. You need to 
                <a href="{moles_record(path)['url']}">apply for access</a>.''')
        status = 403

    if cat_info and cat_info.get("status_warning"):
        messages.warning(request, f'''This data is {cat_info["status"]}! See <a href="{moles_record(path)['url']}">catalogue</a>''')

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
 
    return render(request, template, context, status=status)


@csrf_exempt
def stac(request, path="/"):
    download_service = settings.THREDDS_SERVICE if not settings.USE_FTP else settings.FTP_SERVICE

    path = path.rstrip('/')
    if path == "": 
        path = "/"

    # Check if the request is a file and redirect for direct download
    path_record = get_record(path)
    # print(path_record)
    if path_record is None:
        return render(request, 'browser/notfound.html', {"path": path}, status=404)
    if path_record["type"] == "file": 
        template = 'browser/stac_item.json'
        context = {"path": path}
        return render(request, template, context)

    if path_record["type"] == "link":
        return HttpResponseRedirect(f'/stac?p={path_record["target"]}')

    directories = []
    for item in fbi_listdir(path, dirs_only=True):
        if item["path"] not in settings.DO_NOT_DISPLAY:
            directories.append(item["path"])

    item_paths = []
    items = ls_query(path, item_type="file", size=10000)
    if len(items) < 10000:
        for item in ls_query(path, item_type="file", size=10000):
            item_paths.append(item["path"])

    cat_info = moles_record(path)
    # print(cat_info)
    template = 'browser/stac_catalog.json'
    context = {"path": path, "cat_info": cat_info, "directories": directories,
               "item_paths": item_paths}
    return render(request, template, context)


def get_time_rows(path, time_field, start_date=None, end_date=None):

    query ={"bool": {"must": [
            {"term": {"directory.tree": {"value": path}}},
            {"term": {"type": {"value": "file"}}}
        ],
        "must_not": [{"exists": {"field": "removed"}}]
        }}

    aggs = {"timeline": {"date_histogram": {"field": time_field, "calendar_interval": "day"}}}

    try:
        result = es.search(index=indexname, query=query, aggs=aggs, size=0)
    except Exception as e:
        print(f"Error running elasticsearch query: {e}")
        return {"timeline": {"rows": "", "years": 1, "median_value": 0}, 
                "mod_timeline": {"rows": "", "years": 1, "median_value": 0}}
    
    rows = []
    years = 1
    values = []
    timeline = result["aggregations"]["timeline"]["buckets"]
    if len(timeline) > 0:
        startyear = int(timeline[0]["key_as_string"][:4])
        endyear = int(timeline[-1]["key_as_string"][:4])
        years = endyear - startyear + 1
                        
    for bucket in result["aggregations"]["timeline"]["buckets"]:
        date_str = f"new Date({bucket['key']})"
        value = bucket["doc_count"]
        if value > 0: 
            rows.append(f"[{date_str}, {value}]")
            values.append(value)

    median_value = sorted(values)[len(values)//2] if values else 0  
    return {"rows": ', '.join(rows), "years": years, "median_value": median_value}

@csrf_exempt
def timelines(request, path="/"): 

    path = path.rstrip('/')
    if path == "": 
        path = "/"

    if "time_field" in request.GET and request.GET.get("time_field"):
        time_field = request.GET.get("time_field")
    else: 
        time_field="regex_date"

    # Check if the request is a file and redirect for direct download
    path_record = get_record(path)
    # print(path_record)
    if path_record is None:
        return render(request, 'browser/notfound.html', {"path": path}, status=404)

    template = f'browser/timeline_{time_field}.html'
    tl_tables = get_time_rows(path, time_field)
    context = {"path": path, 
               "time_field": time_field, 
               "timeline": tl_tables["rows"], 
               "scale": tl_tables["median_value"] * 2, 
               "height": tl_tables["years"] * 70 + 100,
               "plot_title": f"Files available by {time_field} date"}

    return render(request, template, context)
    


@csrf_exempt
def jsonlist(request, path="/"):
    download_service = settings.THREDDS_SERVICE if not settings.USE_FTP else settings.FTP_SERVICE
    path = path.rstrip('/')
    if path == "": 
        path = "/"

    # Check if the request is a file and redirect for direct download
    path_record = get_record(path)
    # print(path_record)
    if path_record is None:
        return render(request, 'browser/notfound.html', {"path": path}, status=404)

    if path_record["type"] == "link":
        return HttpResponseRedirect(f'/jsonlist{path_record["target"]}')

    file_recs = ls_query(path, item_type="file", size=10000)
    
    asset_records = {}
    for rec in file_recs:
        asset_records[rec["path"]] = {
            "href": f"{download_service}{rec['path']}?download=1",
      	    "type": "application/data",
            "role": ["data"],
            "size": rec.get("size"),
            "last_modified": rec.get("last_modified")
            }

    return JsonResponse({"filelist": asset_records}, json_dumps_params={"indent": 4})


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
    return HttpResponseRedirect(f"/static/robots.txt")

def search(request):
    print("search...")
    q = ''
    files = []
    if "under" in request.GET and request.GET.get("under"):
        under = request.GET.get("under")
    else: 
        under="/"

    if "since" in request.GET and request.GET.get("since"):
        since = request.GET.get("since")
    else:
        since = None

    if "before" in request.GET and request.GET.get("before"):
        before = request.GET.get("before")
    else:
        before = None

    if "regex_date_since" in request.GET and request.GET.get("regex_date_since"):
        regex_date_since = request.GET.get("regex_date_since")
    else:
        regex_date_since = None

    if "regex_date_before" in request.GET and request.GET.get("regex_date_before"):
        regex_date_before = request.GET.get("regex_date_before")
    else:
        regex_date_before = None    

    if "q" in request.GET and request.GET.get("q"):
        q = request.GET.get("q")
        q_regex = fnmatch.translate(q)[4:-3]
    else:
        q_regex = None

    if "item_type" in request.GET and request.GET.get("item_type"):
        item_type = request.GET.get("item_type")
    else:
        item_type = None

    files = list(ls_query(under, name_regex=q_regex, since=since, before=before, 
                          regex_date_since=regex_date_since, regex_date_before=regex_date_before,
                          item_type=item_type, size=10000))

    return render(request, 'browser/search.html', {"q": q, "results": files, "under": under, "since": since, 
                                                   "before": before, 
                                                   "regex_date_since": regex_date_since, "regex_date_before": regex_date_before,
                                                   "item_type": item_type})

def download(request):
    directory = request.GET.get("path")
    paths = []
    ai = agg_info(directory)
    if ai is not None:
        size = ai["total_size"]
    else:
        size = 0
    for record in ls_query(directory, item_type='file'):
        paths.append(record["path"])
    nfiles = len(paths)
    return render(request, 'browser/download.html', {'download_paths': paths, 
                                                     "size": size, 
                                                     "nfiles": nfiles, 
                                                     "directory": directory})

    
