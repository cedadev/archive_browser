# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '22 Apr 2020'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

from ceda_elasticsearch_tools.elasticsearch import CEDAElasticsearchClient


def str2bool(val):
    string = str(val)
    return string.lower() in ('true') 


def pretty_print(func):
    """
    Decorator to look for pretty=true in the request and add to kwargs
    :param func:
    :return:
    """

    def wrapper(*args, **kwargs):
        request = args[0]
        json_params = kwargs.get('json_params',{})

        if request.GET.get('pretty'):
            if str2bool(request.GET.get('pretty')):
                json_params.update({'indent': 4})

        kwargs['json_params'] = json_params
        res = func(*args, **kwargs)
        return res

    return wrapper

def as_root_path(func):
    """
    Decorator to turn path into an absolute path
    :param func:
    :return:
    """

    def wrapper(*args, **kwargs):
        kwargs['path'] = f'/{kwargs["path"]}'
        res = func(*args, **kwargs)
        return res

    return wrapper


def get_elasticsearch_client():
    return CEDAElasticsearchClient()