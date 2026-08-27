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

#ARCHIVE_ACCESS_TOKEN = "dummy"
HEADER = {"Authorization": f"Bearer {ARCHIVE_ACCESS_TOKEN}"}


TMP_DIR = '/tmp'
DAP_URL = "https://dap.ceda.ac.uk"
MAX_PATH_LENGTH = 300
MAX_QUERY_LENGTH = 20

MAX_FILES = 10000
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

  if query_string:
    regex = f'.*{query_string}.*'
  else:
    regex = None

  if not depth:
    context = { "form_only": True,
                "directory": top_dir,
                "query_string": query_string,
                "depth": MAX_DEPTH}

    return render(request, "list.html", context)

  depth = _validate_depth(depth)

      
  number_ok_files = 0
  number_blocked_files = 0
  number_forbidden_files = 0
  total_size = 0
  max_files_exceeded = False
  max_size_exceeded = False
  file_recs = []
  blocked_recs = []
  forbidden_recs = []

  query_parameters = {"download": "1"}

  session = requests.Session()

  for rec in fbi_core.fbi_records_under(path=top_dir, include_removed=False, item_type='file', name_regex=regex):
    url = DAP_URL + rec['path']

    file_depth = rec['directory'].count('/') - top_dir_path_depth

    if file_depth > depth:
      print ('Too deep: ', rec['path'])
      continue

    if number_ok_files >= MAX_FILES:
      max_files_exceeded = True
      break
    if total_size >= MAX_SIZE:
      max_size_exceeded = True
      break
       
    rec['depth'] = file_depth
    print ('Processing list: ', rec['path'], file_depth)

    response = session.head(url, params=query_parameters, headers=HEADER, allow_redirects=True)

    print ('Resonse url: ', response.url)
    
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


    file_recs.append(rec)
    number_ok_files = number_ok_files + 1
    total_size = total_size + rec['size']

  context = {"nfiles": number_ok_files,
              "number_blocked_files": number_blocked_files,
              "number_forbidden_files": number_forbidden_files,
              "directory": top_dir,
              "size": total_size,
              "file_recs": file_recs,
              "blocked_recs": blocked_recs,
              "forbidden_recs": forbidden_recs,
              "query_string": query_string,
              "depth": depth,
              "max_files": MAX_FILES,
              "max_size": MAX_SIZE, 
              "max_size_exceeded": max_size_exceeded,
              "max_files_exceeded": max_files_exceeded}

  return render(request, "list.html", context)




def download (request):

  top_dir = request.GET.get("path", '').rstrip('/')
  query_string = request.GET.get("query_string", '')
  depth = request.GET.get("depth", MAX_DEPTH)

  if not _validate_path(top_dir):
     return HttpResponse("Not a valid path")

  top_dir_path_depth = top_dir.count('/')

  if not _validate_query(query_string):
     query_string = ''

  depth = _validate_depth(depth)


  if query_string:
    regex = f'.*{query_string}.*'
  else:
    regex = None

  number_ok_files = 0
  total_size = 0
  max_files_exceeded = False
  max_size_exceeded = False


  print ('Depth: ', depth)
  print ('Query: ', query_string)

  query_parameters = {"download": "1"}

  session = requests.Session()

  tmpzip = tempfile.NamedTemporaryFile(suffix='.zip', dir=TMP_DIR, delete=True, delete_on_close=True)
  print ('Zipfile: ', tmpzip.name)
  zip = zipfile.ZipFile(tmpzip.name, mode="w", compresslevel=9, compression=zipfile.ZIP_DEFLATED)

  for rec in fbi_core.fbi_records_under(path=top_dir, include_removed=False, item_type='file', name_regex=regex):
    url = DAP_URL + rec['path']
    print ('Processing download: ', rec['path'], url)

    file_depth = rec['directory'].count('/') - top_dir_path_depth

    if file_depth > depth:
      print ('Too deep: ', rec['path'])
      continue

    if number_ok_files >= MAX_FILES:
      max_files_exceeded = True
      break
    if total_size >= MAX_SIZE:
      max_size_exceeded = True
      break

    response = session.get(url, params=query_parameters, headers=HEADER, allow_redirects=True)

    if response.url.startswith('https://auth.ceda.ac.uk'):
         print ('...Skipping. Login requested', rec['path'])
         continue

    if response.url.endswith('?forbidden'):
         print ('...Forbidden', rec['path'])
         continue

    number_ok_files = number_ok_files + 1
    total_size = total_size + rec['size']

    arc_file_name = rec['path'].lstrip('/')
    zip.writestr(arc_file_name, response.content) 
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

  pattern = r"[a-zA-Z0-9.\-_]+"
  
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
