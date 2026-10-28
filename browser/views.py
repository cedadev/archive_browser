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
import urllib.parse
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

    # Generate button for info action
    info_link = f'<a class="btn" href="/item_info?path={path}" title="Info" data-toggle="tooltip"><i class="fa fa-info-circle"></i> Info</a> '

    if item_type in ("dir", "link"):
        return ""
 
    # Generate button for view action
    view_link = f'<a class="btn" href="{download_service}{path}" title="View file" data-toggle="tooltip"><i class="fa fa-eye"></i> View</a>'

    # Generate button for subset action
    subset_link = f"""<a class='btn' href='{download_service}/thredds/dodsC{path}.html' 
                    title='Extract subset' data-toggle='tooltip'><i class='fa fa-cogs'></i> Subset</a>"""

    if ext in ("nc", ".nc", ".hdf", ".h4", ".hdf4"):
        return subset_link + info_link
    if ext in (".gif", ".jpg", ".jpeg", ".png", ".svg", ".svgz", ".wbmp", ".webp", ".ico", ".jng", ".bmp", ".txt", ".pdf", ".html", ".mp4"):
        return view_link + info_link
    if os.path.basename(path) == '00README':
        return view_link + info_link
    return info_link

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

@lru_cache_expires(maxsize=16384, max_expire_period=2*3600, default=None)
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
                     Dataset {status_badge} {publication_badge}</a>'''
    elif cat_type == "collection":
        return f'''<a href="{cat_url}" class="btn btn-outline-primary btn-sm">
                   <i class="fas fa-copy collection" style="color: #4807b3" title="A collection of Datasets." data-toggle="tooltip"></i> Collection</a>'''    
    elif cat_type == "project":
        return f'''<a href="{cat_url}" class="btn btn-outline-primary btn-sm">
                   <i class="fas fa-users project" style="color: #ea3838" title="A project." data-toggle="tooltip"></i> Project</a>'''


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


@lru_cache_expires(maxsize=16384, max_expire_period=10*3600, default=None)  
def agg_info(path, maxtypes=5, vars_max=1000, max_ext=10):
    print(f"🐸 {path}")
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

def path_view_options(request):
    """For views that use the path and have an advanced option"""
    path = request.path
    advanced = "advanced" in request.GET and bool(request.GET.get("advanced"))
    breadcrumbs = make_breadcrumbs(path, advanced)
    return path, advanced, breadcrumbs

def make_breadcrumbs(path):
    """Make navigation urls and labels."""
    index_list = [{"path": "", "dir": "archive"}]
    if path == "/":
        return index_list

    split_target = path.split('/')[1:]
    for i, dir in enumerate(split_target, 1):
        subset = split_target[:i]
        index_list.append({"path": '/'.join(subset), "dir": dir}) 
    return index_list   

@csrf_exempt
def set_advanced(request):
    """set an advanced session key"""
    redirect = "/"
    advanced = 1 
    if "redirect" in request.GET:
        redirect = request.GET.get("redirect")
    if "advanced" in request.GET:
        advanced = request.GET.get("advanced")
    request.session["advanced"] = advanced
    print(f"ADVANCED SET: {advanced}")
    print(f"session: {request.session.items()}")
    return render(request, 'browser/advanced.html', {"advanced": advanced, "redirect": redirect})

@csrf_exempt
def browse(request):

    path = request.path
    index_list = make_breadcrumbs(path)
    advanced = request.session.get("advanced", 0)
    print(f"ADVANCED: {advanced}")
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

    items = []
    try:
        for item in fbi_listdir(path, removed=advanced, hidden=advanced):
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
        "DOWNLOAD_SERVICE": download_service,
        "advanced": advanced,
    }
 
    return render(request, 'browser/browse_base.html', context, status=status)


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


def get_time_rows(path, time_field):
    """ES quary to grab the date histogram of files in the archive.
       returns a dictionaary containing the things you need for a plot."""
    query ={"bool": {"must": [
            {"term": {"directory.tree": {"value": path}}},
            {"term": {"type": {"value": "file"}}}
        ],
        "must_not": [{"exists": {"field": "removed"}}]
        }}

    aggs = {"timeline": {"date_histogram": {"field": time_field, "calendar_interval": "day"}}}
    print(json.dumps(query, indent=4))
    print(json.dumps(aggs, indent=4))
    try:
        result = es.search(index=indexname, query=query, aggs=aggs, size=0)
    except Exception as e:
        print(f"Error running elasticsearch query: {e}")
        return {"rows": "", "years": 1, "median_value": 0}
    
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

    template = f'browser/timeline.html'
    tl_tables = get_time_rows(path, time_field)
    context = {"path": path, 
            "time_field": time_field, 
            "display": not tl_tables["rows"] == '',
            "timeline": tl_tables["rows"], 
            "scale": tl_tables["median_value"] * 2, 
            "height": tl_tables["years"] * 70 + 100,
            "plot_title": f"Files available by {time_field} date",
            "advanced": request.session.get("advanced", 0),
            "breadcrumbs": make_breadcrumbs(path)}

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
    path = request.GET.get("path")
    path_record = get_record(path)
    if path_record is None:
        render(request, 'browser/notfound.html', {"path": path}, status=404)
    if request.GET.get("json"):
        return JsonResponse(path_record)

    index_list = make_breadcrumbs(path)
    item_type = path_record["type"]
    if item_type == 'file':
        obs_path = path_record["directory"]
    elif item_type == 'link':
        obs_path = path_record["target"]
        target_record = get_record(path_record["target"])
        if target_record and target_record["type"] == "file":
            obs_path = target_record["directory"]
    else:
        obs_path = path

    path_record = json.dumps(path_record, indent=4)
    obs_record = json.dumps(obs_cache[path], indent=4)
    coll_record = json.dumps(collections_cache.get(obs_path), indent=4)
    proj_record = json.dumps(projects_cache.get(obs_path), indent=4)
    context = {"path_record": path_record, "obs": obs_record, "project": proj_record, 
               "coll": coll_record, "item_type": item_type, "path": path, "index_list": index_list } 
    return render(request, 'browser/item_info.html', context)


def cache_control(request):
    context = {"get_access_rules": get_access_rules.cache_info(), 
               "agg": agg_info.cache_info(), 
               "obs_cache_len": len(obs_cache),
               "collections_cache_len": len(collections_cache), 
               "projects_cache_len": len(projects_cache)}
    if "clear_all" in request.GET:
        get_access_rules.cache_clear()
    if "clear" in request.GET:
        path = request.GET.get("clear")
        get_access_rules.cache_clear_key(path)
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

    if "since_last_modified" in request.GET and request.GET.get("since_last_modified"):
        since_last_modified = request.GET.get("since_last_modified")
    else:
        since_last_modified = None

    if "before_last_modified" in request.GET and request.GET.get("before_last_modified"):
        before_last_modified = request.GET.get("before_last_modified")
    else:
        before_last_modified = None

    if "since_regex_date" in request.GET and request.GET.get("since_regex_date"):
        since_regex_date = request.GET.get("since_regex_date")
    else:
        since_regex_date = None

    if "before_regex_date" in request.GET and request.GET.get("before_regex_date"):
        before_regex_date = request.GET.get("before_regex_date")
    else:
        before_regex_date = None    

    if "q" in request.GET and request.GET.get("q"):
        q = request.GET.get("q")
        q_regex = fnmatch.translate(q)[4:-3]
    else:
        q_regex = None

    if "item_type" in request.GET and request.GET.get("item_type"):
        item_type = request.GET.get("item_type")
    else:
        item_type = None

    files = list(ls_query(under, name_regex=q_regex, 
                          since=since_last_modified, 
                          before=before_last_modified, 
                          regex_date_since=since_regex_date, 
                          regex_date_before=before_regex_date,
                          item_type=item_type, size=10000))

    return render(request, 'browser/search.html', {"q": q, "results": files, "under": under, "since_last_modified": since_last_modified, 
                                                   "before_last_modified": before_last_modified, 
                                                   "since_regex_date": since_regex_date, "before_regex_date": before_regex_date,
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

    
