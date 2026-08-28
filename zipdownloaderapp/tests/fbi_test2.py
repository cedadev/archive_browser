import fbi_core
from pathlib import Path
from pprint import pprint
import humanize
from datetime import datetime


start = datetime.now()

TOP_DIR = "/badc/acsoe"

MAX_FILES = 100000
MAX_SIZE = 100000000000000
MAX_DEPTH = 10
GREP = ""
regex = f'.*{GREP}.*'

regex = '.*'

total_size = 0
nfiles = 0


def get_fbi_file_records (top_dir, depth, filter_string='', match_path=False):
#
# Returns fbi records for all files below top_dir matching query
#
    file_recs = []
    total_size = 0
    status = 'OK'

    top_dir.rstrip('/')
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


(status, total_size, file_recs) = get_fbi_file_records (TOP_DIR, 10, filter_string='/weybourne/960929/', match_path=True)

n = 1
for rec in file_recs:
    print (n, rec['path'], rec['name'], rec['size'], rec['depth'])
    n = n + 1

print ('Status: ', status)
print ('Size: ', total_size)
print ('Length: ', len(file_recs))


#
# for rec in fbi_core.fbi_listdir(TOP_DIR, fetch_size=10000, dirs_only=False, removed=False, hidden=False):
#     if rec['type'] != 'file':
#         continue

#for rec in fbi_core.ls_query(TOP_DIR, item_type='file', include_removed=False, exclude_phenomena=False):

#for rec in fbi_core.fbi_records_under(path=TOP_DIR, include_removed=False, item_type='file', exclude_phenomena=False):
#    print (rec['path'], rec['name'], rec['type'], rec['name'], rec['size'])
#    total_size = total_size + rec['size']
#    nfiles = nfiles + 1

# natural_size = humanize.naturalsize(total_size)
# binary_size = humanize.naturalsize(total_size, binary=True)

# print ('Files: ', nfiles)
# print ('Total size: ', natural_size, binary_size, total_size)

print('Time: ', (datetime.now() - start).total_seconds())
