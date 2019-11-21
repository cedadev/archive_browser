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
from django.urls import path, re_path
from . import views

urlpatterns = [
    re_path('^show_all/(?P<path>.*)/$', views.show_all, name='show_all' ),
    re_path('^show_all/(?P<path>.*)', views.show_all, name='show_all' ),
    path('storage_types', views.storage_types, name='storage_types'),
    re_path('.*', views.browse, name='browse' ),
]

