from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect

import fbi_core

import requests
import tempfile
import zipfile
import os
from pprint import pprint


TOKEN = "dummy"
HEADER = {"Authorization": f"Bearer {TOKEN}"}


ZIPFILE = '/tmp/ceda_download.zip'
DAP_URL = "https://dap.ceda.ac.uk"


def list (request):


  top_dir = "/badc/ukmo-midas/data/CURL/yearly_files"
  top_dir = request.GET.get("path")
  if not top_dir:
     return HttpResponse("No path specified")



  cookies = {"ceda.session.1": request.COOKIES.get('ceda.session.1'),
              "ceda.session.2": request.COOKIES.get('ceda.session.2'),
              "auth_tkt": request.COOKIES.get('auth_tkt'),
              }

  query_parameters = {"download": "1"}

  session = requests.Session()

  for rec in fbi_core.fbi_records_under(path=top_dir, include_removed=False, item_type='file'):
    url = DAP_URL + rec['path']
    print ('Processing: ', rec['path'], url)

    response = session.head(url, params=query_parameters, headers=HEADER, cookies=cookies, allow_redirects=True)

    if response.url.startswith('https://auth.ceda.ac.uk'):
         print ('...Skipping', rec['path'])
         continue

  return HttpResponse("Hello, world. You're at the polls index.")




def download (request):

  top_dir = "/badc/ukmo-midas/data/CURL/yearly_files"

  cookies = {"ceda.session.1": request.COOKIES.get('ceda.session.1'),
              "ceda.session.2": request.COOKIES.get('ceda.session.2'),
              "auth_tkt": request.COOKIES.get('auth_tkt'),
              }

  query_parameters = {"download": "1"}

  session = requests.Session()

  zip = zipfile.ZipFile(ZIPFILE, mode="w", compresslevel=9, compression=zipfile.ZIP_DEFLATED)


  for rec in fbi_core.fbi_records_under(path=top_dir, include_removed=False, item_type='file'):
    url = DAP_URL + rec['path']
    print ('Processing: ', rec['path'], url)

    response = session.get(url, params=query_parameters, headers=HEADER, cookies=cookies, allow_redirects=True)

    if response.url.startswith('https://auth.ceda.ac.uk'):
         print ('...Skipping', rec['path'])
         continue

    arc_file_name = rec['path'].lstrip('/')
    zip.writestr(arc_file_name, response.content) 

  zip.close()
  response = FileResponse(open(ZIPFILE, "rb"), as_attachment=True)

  return response


def index(request):

    cookies = {"ceda.session.1": request.COOKIES.get('ceda.session.1'),
               "ceda.session.2": request.COOKIES.get('ceda.session.2'),
               "auth_tkt": request.COOKIES.get('auth_tkt'),
               }

    url =  "https://dap.ceda.ac.uk/badc/ukmo-midas/data/CURL/yearly_files/midas_clm-ua-rec_200701-200712.txt"
    query_parameters = {"download": "1"}

   # session = requests.Session()

    #pprint(vars(session))

    response = session.get(url, params=query_parameters, headers=HEADER, cookies=cookies)

    downfile = "/tmp/mydownload.txt"
    myzipfile = "/tmp/myzipfile.zip"

    with open(downfile, mode="wb") as file:
        file.write(response.content)

    #tmp = tempfile.TemporaryFile(suffix='.zip')
    #tmp = tempfile.mkstemp(suffix=".zip")
    #¢filename = os.path.basename(downfile)

    tf = zipfile.ZipFile(myzipfile, mode="w")
    tf.write(downfile)
    tf.close()

  #  fh = zipfile.ZipFile(myzipfile, mode="r")

    response = FileResponse(open(myzipfile, "rb"), as_attachment=True)


   # return HttpResponse("Hello, world. You're at the polls index.")
    tf.close()
    return response
