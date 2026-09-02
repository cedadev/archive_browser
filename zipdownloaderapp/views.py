from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render

import fbi_core

import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import re
import tempfile
import zipfile
import os
from pprint import pprint
from archive_browser.settings import  ARCHIVE_ACCESS_TOKEN

#ARCHIVE_ACCESS_TOKEN = "dummy"
HEADER = {"Authorization": f"Bearer {ARCHIVE_ACCESS_TOKEN}"}


TMP_DIR = '/tmp'
DAP_URL = "https://dap.ceda.ac.uk"
MAX_PATH_LENGTH = 300
MAX_QUERY_LENGTH = 20

MAX_FILES = 1000000
MAX_SIZE = 10000000000
MAX_DEPTH = 10



def list (request):

  top_dir = request.GET.get("path", '').rstrip('/')
  query_string = request.GET.get("query_string", '')
  depth = request.GET.get("depth", None)

  if not _validate_path(top_dir):
     return HttpResponse("Not a valid path")

  top_dir_path_depth = top_dir.count('/')

  if not _validate_query(query_string):
     query_string = ''

  print ('Path: ', top_dir, 'Depth: ', depth, 'Query string: ', query_string)

#
# Just display the form, no results to return
#
  if not depth:
    context = { "form_only": True,
                "directory": top_dir,
                "query_string": query_string,
                "depth": 0}

    return render(request, "list.html", context)

  depth = _validate_depth(depth)

  (status, total_size, fbi_records) = _get_fbi_file_records (top_dir, depth, filter_string=query_string, match_path=False)

  print ('Recs: ', len(fbi_records))
  number_ok_files = 0
  size = 0
  number_blocked_files = 0
  number_forbidden_files = 0
  max_files_exceeded = False
  max_size_exceeded = False
  ok_file_recs = []
  blocked_recs = []
  forbidden_recs = []

  query_parameters = {"download": "1"}
  session = requests.Session()

  retries = Retry(
    total=3,
    backoff_factor=0.1,
    status_forcelist=[502, 503, 504],
    allowed_methods={'GET'},
  )
  session.mount('https://', HTTPAdapter(max_retries=retries))

  nrecords = 1

  for rec in fbi_records:
    url = DAP_URL + rec['path'] 
    print (f'Processing {nrecords} of ', len(fbi_records), rec['path'], rec['depth'])

    response = session.head(url, params=query_parameters, headers=HEADER, allow_redirects=True)

   # print ('Resonse url: ', response.url)
    
    if response.url.startswith('https://auth.ceda.ac.uk'):
         print ('...Skipping - login required', rec['path'])
         number_blocked_files = number_blocked_files + 1
         blocked_recs.append(rec)
         continue

    if response.url.endswith('?forbidden'):
         print ('...Forbidden', rec['path'])
         number_forbidden_files = number_forbidden_files + 1
         forbidden_recs.append(rec)
         continue

    ok_file_recs.append(rec)
    number_ok_files = number_ok_files + 1
    nrecords = nrecords + 1
    size = size + rec['size']

  context = {"nfiles": number_ok_files,
              "number_blocked_files": number_blocked_files,
              "number_forbidden_files": number_forbidden_files,
              "directory": top_dir,
              "size": size,
              "file_recs": ok_file_recs,
              "blocked_recs": blocked_recs,
              "forbidden_recs": forbidden_recs,
              "query_string": query_string,
              "depth": depth,
              "max_files": MAX_FILES,
              "max_size": MAX_SIZE, 
              "max_size_exceeded": status == 'max_size_exceeded',
              "max_files_exceeded": status == 'max_files_exceeded'}

  return render(request, "list.html", context)




def download (request):

  top_dir = request.GET.get("path", '').rstrip('/')
  query_string = request.GET.get("query_string", '')
  depth = request.GET.get("depth", MAX_DEPTH)

  if not _validate_path(top_dir):
     return HttpResponse("Not a valid path")

  if not _validate_query(query_string):
     query_string = ''

  print ('Path: ', top_dir, 'Depth: ', depth, 'Query string: ', query_string)

  depth = _validate_depth(depth)

  (status, total_size, fbi_records) = _get_fbi_file_records (top_dir, depth, filter_string=query_string, match_path=False)

  query_parameters = {"download": "1"}
  session = requests.Session()

  retries = Retry(
    total=3,
    backoff_factor=0.1,
    status_forcelist=[502, 503, 504],
    allowed_methods={'GET'},
  )
  session.mount('https://', HTTPAdapter(max_retries=retries))

  tmpzip = tempfile.NamedTemporaryFile(suffix='.zip', dir=TMP_DIR, delete=True, delete_on_close=True)
  print ('Zipfile: ', tmpzip.name)
  zip = zipfile.ZipFile(tmpzip.name, mode="w", compresslevel=9, compression=zipfile.ZIP_DEFLATED)

  ndownload = 1

  for rec in fbi_records:
    url = DAP_URL + rec['path']
    print (f'Processing download: {ndownload} of ', len(fbi_records), rec['path'])

    response = session.get(url, params=query_parameters, headers=HEADER, allow_redirects=True)

    if response.url.startswith('https://auth.ceda.ac.uk'):
         print ('...Skipping. Login requested', rec['path'])
         continue

    if response.url.endswith('?forbidden'):
         print ('...Forbidden', rec['path'])
         continue

    arc_file_name = rec['path'].lstrip('/')
    zip.writestr(arc_file_name, response.content) 

    ndownload = ndownload +1
#
# Return zipfile as an attachment
#
  zip.close()
  response = FileResponse(tmpzip, filename='ceda_download.zip', as_attachment=True)
  return response



def _validate_path (path):
#
# Do some checks on the given path to make sure it is ok to proceed with
#
  pattern = r"[a-zA-Z0-9/.\-_]+"
  
  if re.fullmatch(pattern, path) and len(path) <= MAX_PATH_LENGTH:
      return True
  else:
      return False


def _validate_query(query):

  pattern = r"[a-zA-Z0-9./\-_]+"
  
  if re.fullmatch(pattern, query) and len(query) <= MAX_QUERY_LENGTH:
      return True
  else:
      return False


def _validate_depth(depth_string):

  depth = MAX_DEPTH

  try:
    depth = int(depth_string)

    if depth > MAX_DEPTH:
       depth = MAX_DEPTH
    if depth < 0:
       depth = 0   
  except:
    pass

  return depth


def _get_fbi_file_records (top_dir, depth, filter_string='', match_path=False):
#
# Returns fbi records for all files below top_dir matching query
#
    file_recs = []
    total_size = 0
    status = 'OK'

    top_dir = top_dir.rstrip('/')
    top_dir_path_depth = top_dir.count('/')
#
#   Use listdir if we only want a single directory as it will be faster
#  
    if depth == 0:
        records = fbi_core.fbi_listdir(top_dir, fetch_size=10000, dirs_only=False, removed=False, hidden=False)
    else:
        records = fbi_core.fbi_records_under(path=top_dir, include_removed=False, item_type='file', exclude_phenomena=True)

    for rec in records:
        if rec['type'] != 'file':
            continue

        file_depth = rec['directory'].count('/') - top_dir_path_depth
        rec['depth'] = file_depth

        if filter_string:
            if match_path:
                if not filter_string in rec['path']: continue
            else:
                if not filter_string in rec['name']: continue

        if file_depth > depth:
            continue

        if len(file_recs) >= MAX_FILES:
            status = 'max_files_exceeded'
            break
        if total_size >= MAX_SIZE:
            status = 'max_size_exceeded'
            break

        file_recs.append(rec)
        total_size = total_size + rec['size']

    return (status, total_size, file_recs)
