# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '22 Apr 2020'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'


def generate_exceptions(exceptions):
    """
    Filter results based on exceptions
    :param exceptions:
    :return:
    """

    # Hide . directories
    must_not = [{
        "regexp": {
            "dir.keyword": "[.].*"
        }
    }]

    for exception in exceptions:
        must_not.append(
            {
                'term': {
                    'path.keyword': exception
                }
            }
        )

    return must_not