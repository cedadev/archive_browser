"""data_broswer URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.urls import path, re_path, include
from django.shortcuts import HttpResponse
from . import views


def health_view(request):
    return HttpResponse("OK")


urlpatterns = [
    path('health/', health_view, name='health'),
    #re_path('^api/directory/(?P<path>.*)', views.get_directories, name='directories'),
    #re_path('^api/file/(?P<path>.*)', views.get_files, name='files'),
    path('storage_types', views.storage_types, name='storage_types'),
    path('robots.txt', views.robots, name='robots'),
    path('cache', views.cache_control, name='cache'),
    path('search', views.search, name='search'),
    path('item_info', views.item_info, name='item_info'),
    path('oidc/', include('mozilla_django_oidc.urls')),
    re_path('.*', views.browse, name='browse' ),
]

#urlpatterns = [
#    re_path('^api/directory/(?P<path>.*)', views.get_directories, name='directories'),
#    re_path('^api/file/(?P<path>.*)', views.get_files, name='files'),
#    #url('^api/directory/(?<datacenter>[a-z-]+>/$','views.browser'),
#    path('storage_types', views.storage_types, name='storage_types'),
#    path('robots.txt', views.RobotsTxt.as_view(), name='robots'),
#    re_path('.*', views.browse, name='browse' ),
#]

