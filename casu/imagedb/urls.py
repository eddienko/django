from django.conf.urls import patterns, url

from imagedb import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^getImageLocal$', views.getImageLocal, name='getImageLocal'),
    url(r'^getImageCache/(?P<md5hash>\S+)$', views.getImageCache, name='getImageCache'),
    url(r'^getImage$', views.getImage, name='getImage'),    
)