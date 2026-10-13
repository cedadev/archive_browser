from browser.treedict import TreeDict 
import time
import json
import urllib.request
import threading
import time
import os
from collections import defaultdict, Counter
import datetime

# feilds to keep from the catalogue records
KEEP_FIELDS = ("title", "uuid", "ob_id", "publicationState", "status")
REFRESH = 30

def records_for_path_parent(path_to_uuid: dict[str, set], path: str, uuids: set[str]):
    """Find paths that are unambiguously associated with a single observation/project."""
    if path == "/":
        return
    parent = os.path.dirname(path)
    if parent not in path_to_uuid:
        path_to_uuid[parent] = set(uuids) 
    else:
        path_to_uuid[parent].intersection_update(uuids)  # Keep only the uuids that are common to all children
    records_for_path_parent(path_to_uuid, parent, path_to_uuid[parent])  # Recurse up the tree

def find_record_paths(path_to_uuid: dict, path: str, uuid: str, title: str):
    """Find paths that are unambiguously associated with a single observation/project."""
    while path != "/":
        path = os.path.dirname(path)
        if path not in path_to_uuid:
            path_to_uuid[path] = {"uuid": uuid, "title": title}    # If the path is not in the dictionary, add it with the current uuid and title
        elif path_to_uuid[path] is None:
            continue                                               # If the path is already marked as ambiguous, do nothing
        elif path_to_uuid[path]["uuid"] == uuid:
            continue                                               # If the path already has the same uuid, do nothing
        else: 
            path_to_uuid[path] = None                              # Blank out the path if it has more than one uuid associated with it


def obs(obs_store, coll_store, proj_store, mod_since):
    """Populate obs store and collection store dictionaries from the catalogue."""

    if mod_since is not None:
        mod_str = f"&lastUpdatedDate__gt={mod_since}"
    else:
        mod_str = ""
    url = f"https://catalogue.ceda.ac.uk/api/v3/observations/?limit=300{mod_str}"
    collection_paths = defaultdict(list)
    collection_records = {}    
    project_paths = defaultdict(list)
    project_records = {}
    collection_sets = defaultdict(set)
    project_sets = defaultdict(set) 
  
    while True:
        print(url)
        try: 
            page = urllib.request.urlopen(url)
        except urllib.error.HTTPError:
            time.sleep(2)
            continue
        data = json.loads(page.read().decode())
        page.close()
        for record in data["results"]:
            if "result_field" in record and record["result_field"] and "dataPath" in record["result_field"]:
                cutdown = {}
                for field in KEEP_FIELDS:
                    cutdown[field] = record.get(field, None)
                path = record["result_field"]["dataPath"]
                if path.startswith('/'):
                    obs_store[path] = cutdown

                    # count collections and projects for each path
                    coll_uuids = set(coll["uuid"] for coll in record.get("observationcollection_set", []))
                    proj_uuids = set(proj["uuid"] for proj in record.get("projects", []))
                    records_for_path_parent(collection_sets, path, coll_uuids)
                    records_for_path_parent(project_sets, path, proj_uuids)
                    for coll in record["observationcollection_set"]:
                        collection_records[coll["uuid"]] = coll
                    for proj in record["projects"]:
                        project_records[proj["uuid"]] = proj
                        
        if "next" not in data or data["next"] is None:
            break
        else:
            url = data["next"]

    # sort collection info
    for path, uuids in collection_sets.items():
        if len(uuids) == 1:
            uuid = uuids.pop()
            coll_store[path] = {"title": collection_records[uuid]["title"], "uuid": uuid}

    for path, uuids in project_sets.items():
        if len(uuids) == 1:
            uuid = uuids.pop()
            proj_store[path] = {"title": project_records[uuid]["title"], "uuid": uuid}

            
def cache_obs_loop(obs_store, coll_store, proj_store):
    """Loop forever cacheing the list of observations"""
    mod_since = None
    while True:
        # print(mod_since)
        obs(obs_store, coll_store, proj_store, mod_since)
        time.sleep(REFRESH)
        mod_since = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()

def observation_cache():
    obs_store = TreeDict()
    coll_store = {}
    project_store = {}
    t = threading.Thread(target=cache_obs_loop, args=(obs_store, coll_store, project_store), daemon=True)
    t.start()
    return obs_store, coll_store, project_store

    
if __name__ == "__main__":
    s, c, p = observation_cache()
    while True:
        print(len(s), len(c), len(p))
#        print(c)
        time.sleep(1)
