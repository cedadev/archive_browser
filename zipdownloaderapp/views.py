from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render

import fbi_core

import requests
import tempfile
import zipfile
import os
from pprint import pprint
from archive_browser.settings import  ARCHIVE_ACCESS_TOKEN


HEADER = {"Authorization": f"Bearer {ARCHIVE_ACCESS_TOKEN}"}


ZIPFILE = '/tmp/ceda_download.zip'
DAP_URL = "https://dap.ceda.ac.uk"


def list (request):

  top_dir = request.GET.get("path", '')

  if not top_dir:
    return HttpResponse("No path specified")

  SEARCH_STRING = "acsoe"
  regex = f'.*{SEARCH_STRING}.*'

  number_ok_files = 0
  number_blocked_files = 0
  total_size = 0
  file_recs = []
  blocked_recs = []

  query_parameters = {"download": "1"}

  session = requests.Session()

  for rec in fbi_core.fbi_records_under(path=top_dir, include_removed=False, item_type='file', name_regex=regex):
    url = DAP_URL + rec['path']
    print ('Processing: ', rec['path'], url)

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
              "blocked_recs": blocked_recs}

  return render(request, "list.html", context)




def download (request):


  top_dir = request.GET.get("path", '')

  if not top_dir:
    return HttpResponse("No path specified")


  query_parameters = {"download": "1"}

  session = requests.Session()

  zip = zipfile.ZipFile(ZIPFILE, mode="w", compresslevel=9, compression=zipfile.ZIP_DEFLATED)

  for rec in fbi_core.fbi_records_under(path=top_dir, include_removed=False, item_type='file'):
    url = DAP_URL + rec['path']
    print ('Processing: ', rec['path'], url)

    response = session.get(url, params=query_parameters, headers=HEADER, allow_redirects=True)

    if response.url.startswith('https://auth.ceda.ac.uk'):
         print ('...Skipping', rec['path'])
         continue

    arc_file_name = rec['path'].lstrip('/')
    zip.writestr(arc_file_name, response.content) 

  zip.close()
  response = FileResponse(open(ZIPFILE, "rb"), as_attachment=True)

  return response


