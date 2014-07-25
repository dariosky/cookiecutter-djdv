from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.views.generic.base import TemplateView

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='home.html'), name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
)



def errorview(request):
	raise Exception("Test exception")


handler404 = '{{cookiecutter.repo_name}}.views.errors404'
handler500 = '{{cookiecutter.repo_name}}.views.errors505'

urlpatterns += patterns('',
                        url('^500/', errorview, name='error-test')
)
