from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'casu.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', 'casu.views.home', name='home'),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^imagedb/', include('imagedb.urls', namespace='imagedb')),

)
