from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render

import fbi_core

import requests
import re
import tempfile
import zipfile
import os
from pprint import pprint
from archive_browser.settings import  ARCHIVE_ACCESS_TOKEN


HEADER = {"Authorization": f"Bearer {ARCHIVE_ACCESS_TOKEN}"}


ZIPFILE = '/tmp/ceda_download.zip'
DAP_URL = "https://dap.ceda.ac.uk"
MAX_PATH_LENGTH = 300
MAX_QUERY_LENGTH = 20

MAX_FILES = 10
MAX_SIZE = 100000000000

    

def list (request):

  top_dir = request.GET.get("path", '')
  query_string = request.GET.get("query_string", '')
  depth = request.GET.get("depth", 10)

  if not _validate_path(top_dir):
     return HttpResponse("Not a valid path")

  top_dir_path_depth = top_dir.count('/')

  if not _validate_query(query_string):
     query_string = ''

  regex = f'.*{query_string}.*'

  number_ok_files = 0
  number_blocked_files = 0
  total_size = 0
  file_recs = []
  blocked_recs = []

  query_parameters = {"download": "1"}

  session = requests.Session()

  for rec in fbi_core.fbi_records_under(path=top_dir, include_removed=False, item_type='file', name_regex=regex):
    url = DAP_URL + rec['path']

    if number_ok_files >= MAX_FILES or total_size >= MAX_SIZE:
        break

    depth = rec['directory'].count('/') - top_dir_path_depth
    print ('Processing: ', rec['path'], depth)

    response = session.head(url, params=query_parameters, headers=HEADER, allow_redirects=True)

    if response.url.startswith('https://auth.ceda.ac.uk'):
         print ('...Skipping', rec['path'])
         number_blocked_files = number_blocked_files + 1
         blocked_recs.append(rec)
         continue

    file_recs.append(rec)
    number_ok_files = number_ok_files + 1
    total_size = total_size + rec['size']

  context = {"nfiles": number_ok_files,
              "number_blocked_files": number_blocked_files,
              "directory": top_dir,
              "size": total_size,
              "file_recs": file_recs,
              "blocked_recs": blocked_recs,
              "query_string": query_string}

  return render(request, "list.html", context)




def download (request):

  top_dir = request.GET.get("path", '')
  query_string = request.GET.get("query_string", '')

  if not _validate_path(top_dir):
     return HttpResponse("Not a valid path")

  top_dir_path_depth = top_dir.count('/')

  if not _validate_query(query_string):
     query_string = ''

  regex = f'.*{query_string}.*'

  print ('Query_string: ', query_string)


  query_parameters = {"download": "1"}

  number_ok_files = 0
  total_size = 0

  session = requests.Session()

  zip = zipfile.ZipFile(ZIPFILE, mode="w", compresslevel=9, compression=zipfile.ZIP_DEFLATED)

  for rec in fbi_core.fbi_records_under(path=top_dir, include_removed=False, item_type='file', name_regex=regex):
    url = DAP_URL + rec['path']
    print ('Processing: ', rec['path'], url)

    response = session.get(url, params=query_parameters, headers=HEADER, allow_redirects=True)

    if response.url.startswith('https://auth.ceda.ac.uk'):
         print ('...Skipping', rec['path'])
         continue

    number_ok_files = number_ok_files + 1
    total_size = total_size + rec['size']

    arc_file_name = rec['path'].lstrip('/')
    zip.writestr(arc_file_name, response.content) 

  zip.close()
  response = FileResponse(open(ZIPFILE, "rb"), as_attachment=True)

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

  pattern = r"[a-zA-Z0-9.\-_]+"
  
  if re.fullmatch(pattern, query) and len(query) <= MAX_QUERY_LENGTH:
      return True
  else:
      return False

