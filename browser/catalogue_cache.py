

import os
import requests
from typing import DefaultDict
import threading
import time

def collection_details(coll_id):
    """return collection details"""
    return COLL_DETAILS.get(coll_id)

def get_observation(path):
    """get observation info for a given path, searching up the directory tree if needed"""
    get_records_if_needed()
    ob = None
    p = path
    print(len(OBS_CACHE), len(COLL_CACHE))
    while p != "/":
        if OBS_CACHE and path in OBS_CACHE:
            ob = OBS_CACHE[p]
            break
        p = os.path.dirname(p)

    if COLL_CACHE and path in COLL_CACHE:
        return ob, list(COLL_CACHE[path])
    else:
        return ob, []

OBS_CACHE: dict = {}
COLL_CACHE: DefaultDict = DefaultDict(set)
COLL_DETAILS: dict = {}

def get_records_if_needed():
    """Run a thread to grab the records in the background if not already running"""
    if get_records_if_needed.CACHE_THREAD and get_records_if_needed.CACHE_THREAD.is_alive():
        return
    if get_records_if_needed.CACHE_RECHECK_TIME > time.time():
        return
    get_records_if_needed.CACHE_THREAD = threading.Thread(target=fetch_catalogue_records)
    get_records_if_needed.CACHE_THREAD.daemon = True
    get_records_if_needed.CACHE_THREAD.start()
    get_records_if_needed.CACHE_RECHECK_TIME = time.time() + 3600

get_records_if_needed.CACHE_THREAD = None
get_records_if_needed.CACHE_RECHECK_TIME = 0

def fetch_catalogue_records():
    """get a dict of observations from the MOLES API"""

    print(f"runnig get_observation_dict ")
    fields = "member,updateFrequency,status,publicationState,uuid,title,permissions,result_field,observationcollection_set"
    state_filters = "&publicationState__in=published,citable,old,removed"
    result_field_filters = "&result_field__storageLocation=internal&result_field__storageStatus=online"
    api_base_url = f"https://catalogue.ceda.ac.uk/api/v3/observations.json/?limit=500&fields={fields}{state_filters}{result_field_filters}"
    
    url = api_base_url
    observations = []

    while True:
        resp = requests.get(url)
        
        if resp.status_code == 200:
            json_content = resp.json()
            observations.extend(json_content['results'])

        if "next" in json_content and json_content["next"]:
            url = json_content["next"]
        else:
            break

    tmp_obs_cache = {}
    for obs in observations:
        tmp_obs_cache[obs['result_field']['dataPath']] = obs

    # make collections by path
    tmp_coll_cache = DefaultDict(set)
    for path, observation in tmp_obs_cache.items():
        for coll_id in observation["observationcollection_set"]:
            p = path
            while p != "/":
                tmp_coll_cache[p].add(coll_id)
                p = os.path.dirname(p)

    # just keep the ones with a single collections  
    for path, colls in tmp_coll_cache.copy().items():
        if len(colls) > 1:
            del tmp_coll_cache[path]

    #print(observation_dict)
    print(len(COLL_CACHE))
    OBS_CACHE.clear()
    OBS_CACHE.update(tmp_obs_cache)
    COLL_CACHE.clear()
    COLL_CACHE.update(tmp_coll_cache)

    # get collection details
    fields = "uuid,title,publicationState,ob_id"
    state_filters = "&publicationState__in=published,citable,old,removed"
    api_base_url = f"https://catalogue.ceda.ac.uk/api/v3/observationcollections.json/?limit=500&fields={fields}{state_filters}"
    url = api_base_url
    observationscollections = []

    while True:
        resp = requests.get(url)
        if resp.status_code == 200:
            json_content = resp.json()
            observationscollections.extend(json_content['results'])
        if "next" in json_content and json_content["next"]:
            url = json_content["next"]
        else:
            break
   
    tmp_observationcollections_dict = {}
    for collection in observationscollections:
        tmp_observationcollections_dict[collection['ob_id']] = collection
    COLL_DETAILS.clear()
    COLL_DETAILS.update(tmp_observationcollections_dict)


if __name__ == "__main__":
    for i in range(100):
        print(len(OBS_CACHE), len(COLL_CACHE), len(COLL_DETAILS))
        get_records_if_needed()
        time.sleep(1)

        print(get_observation("/badc/acsoe/data"))    
     