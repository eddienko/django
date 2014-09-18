from django.conf.urls import patterns, url

from imagedb import views

urlpatterns = patterns('',
    url(r'^index$', views.index, name='index'),
    url(r'^getImageLocal$', views.getImageLocal, name='getImageLocal'),
    url(r'^getImageCache/(?P<md5hash>\S+)$', views.getImageCache, name='getImageCache'),
    url(r'^getImage$', views.getImage, name='getImage'),
    url(r'^collection', views.collection, name='collection'),
    url(r'^getTar/(?P<md5hash>\S+)$', views.getTar, name='getTar'),
    url(r'^showField', views.showField, name='showField'),
    url(r'^getStatus/(?P<id>\S+)$', views.getStatus, name='getStatus'),
)