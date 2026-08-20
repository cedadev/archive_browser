import fbi_core
from pathlib import Path
from pprint import pprint
import humanize
from datetime import datetime


start = datetime.now()

TOP_DIR = "/badc/ukmo-midas/data/MO"
GREP = ""
regex = f'.*{GREP}.*'

regex = '.*'

total_size = 0
nfiles = 0
for rec in fbi_core.fbi_records_under(path=TOP_DIR, include_removed=False, item_type='file',  name_regex=regex, fetch_size=1000):
    print (rec['path'], rec['size'])
    total_size = total_size + rec['size']
    nfiles = nfiles + 1

natural_size = humanize.naturalsize(total_size)
binary_size = humanize.naturalsize(total_size, binary=True)

print ('Files: ', nfiles)
print ('Total size: ', natural_size, binary_size, total_size)

print('Time: ', (datetime.now() - start).total_seconds())
