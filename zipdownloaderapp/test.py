from django.http import FileResponse

import requests
import tempfile
import zipfile
import os



url = "https://dap.ceda.ac.uk/badc/acsoe/doc/00README"
query_parameters = {"download": "1"}
response = requests.get(url, params=query_parameters)

downfile = "/Users/andrew.harwood/Development/zip-downloader/src/zipdownloaderapp/myfile.out"
myzipfile = "/tmp/myzipfile.zip"

with open(downfile, mode="wb") as file:
    file.write(response.content)

#tmp = tempfile.TemporaryFile(suffix='.zip')
#tmp = tempfile.mkstemp(suffix=".zip")
#¢filename = os.path.basename(downfile)

tf = zipfile.ZipFile(myzipfile, mode="w")
tf.write(downfile)
tf.close()

response = FileResponse(file_handle, as_attachment=True)

return response
    # response = HttpResponse(File(file(tmp[1])), mimetype="application/zip")
    #     response['Content-disposition'] = ('attachment; '
    #                                        'filename="{}"').format(os.path.basename(tmp[1]))

