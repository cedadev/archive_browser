import os
import requests
import json
from collections import defaultdict
import re

def get_collection_info2():
    r = requests.get("https://catalogue.ceda.ac.uk/api/v2/observations.json/?fields=uuid,title,result_field,status,observationcollection_set&limit=20000")

    # map collections to paths
    description_records = {}
    collections_paths = defaultdict(list)
    for rec in r.json()["results"]:
        # skip records with no results field
        if "result_field" not in rec or rec["result_field"] is None:
            continue
        # skip records with bad data path
        if "dataPath" not in rec["result_field"] or not rec["result_field"]["dataPath"].startswith("/"):
            continue
        data_path = rec["result_field"]["dataPath"]
 
        # description records are observation records mostly
        description_records[data_path] = rec

        for collection_url in rec["observationcollection_set"]:
            coll_id = int(re.search(r'/(\d+)\.json$', collection_url).group(1))
            collections_paths[coll_id].append(data_path)

    # find collections common paths
    collections_common_paths = {}
    for coll_id, paths in collections_paths.items():
        collections_common_paths[coll_id] = os.path.commonpath(paths)

    # invert the dict
    common_paths_collections = defaultdict(list)
    for coll_id, common_path in collections_common_paths.items():
        common_paths_collections[common_path].append(coll_id)

    # find unambiguous common paths to map common path to collections
    unique_path_collection_map = {}
    for common_path, collections_list in common_paths_collections.items():
        if len(collections_list) == 1:
            unique_path_collection_map[common_path] = collections_list[0]

    # grab collections records
    r = requests.get("https://catalogue.ceda.ac.uk/api/v2/observationcollections.json/?limit=10000&fields=ob_id,uuid,title,publicationState")
    collection_records = {}
    for rec in r.json()["results"]:
        collection_records[rec["ob_id"]] = rec

    #  fold collection records into observation record descriptions
    for path, coll_id in unique_path_collection_map.items():
        # ignore collection records that are single observation records
        if path in description_records:
            continue
        else: 
            description_records[path] = collection_records[coll_id]

    return description_records    


cache = {"/badc/faam": {"expires": "2024-10-18T12:00:00", "collection": {"title": "ffff"}},
         "/badc/faam/data/2023/b-123": {"expires": "2024-10-18T12:00:00",
                                        "dataset": {"title": "B123", "status": "complete"}}}


def get_member(member):
    print(member)
    r = requests.get(member + "?fields=uuid,title,result_field,status")

    print(r.json())

def get_collections_info():
    r = requests.get("https://catalogue.ceda.ac.uk/api/v2/observationcollections.json/?limit=10")
    for rec in r.json()["results"]:
        print(rec['title'])
        for member in rec['member']:
            get_member(member)


# look up info like this
records = {"/badc/x/y/z": {"b": 4},
           "/badc/x/y/A": {"a": 111, "b": 222},
           "/badc/x": {"a": 10}}

def lookup(path):

    path = os.path.normpath(path)
    matches = []
    while path != "/":
        print(path)
        if path in records:
            matches.insert(0, records[path])
        path = os.path.dirname(path)
    
    combined_rec = {}
    for rec in matches:
        combined_rec.update(rec)
    return combined_rec

if __name__ == "__main__":

    print(lookup("/badc/x/y/z"))
    # {"a": 10, "b": 4}
    print(lookup("/badc/x"))
    # {"a": 10}
    print(lookup("/badc/x/y/z/ffff/ggg"))
    # {"a": 10, "b":4}
    print(lookup("/badc/x/y/A"))
    # {"a": 111, "b": 222}


    get_collection_info2()
