from django.conf.urls import patterns, url, include

from accounts import views

urlpatterns = patterns('',
    url(r'', include('django.contrib.auth.urls')),
    url(r'^register', views.register, name='register'),
    #url(r'^login/$', 'django.contrib.auth.views.login',  name='login'),
    #url(r'^login$', 'django.contrib.auth.views.login', {'template_name': 'accounts/login.html'}),
    #url(r'^logout$', 'django.contrib.auth.views.logout', {'next_page': '/'}),
    #url(r'^password_change$', 'django.contrib.auth.views.password_change', {'template_name': 'accounts/password_change_form.html'}),
    #url(r'^password_change_done$', 'django.contrib.auth.views.password_change_done', {'template_name': 'accounts/password_change_done.html'}),
)