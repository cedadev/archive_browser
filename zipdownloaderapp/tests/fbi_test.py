import fbi_core
from pathlib import Path
from pprint import pprint
import humanize
from datetime import datetime


start = datetime.now()

TOP_DIR = "/badc/cmip5"
GREP = ""
regex = f'.*{GREP}.*'

regex = '.*'

total_size = 0
nfiles = 0
for rec in fbi_core.fbi_records_under(path=TOP_DIR, include_removed=False, item_type='link',  name_regex=None, fetch_size=1000):
    print (rec['path'], rec['name'])
#    total_size = total_size + rec['size']
    nfiles = nfiles + 1

natural_size = humanize.naturalsize(total_size)
binary_size = humanize.naturalsize(total_size, binary=True)

print ('Files: ', nfiles)
print ('Total size: ', natural_size, binary_size, total_size)

print('Time: ', (datetime.now() - start).total_seconds())
