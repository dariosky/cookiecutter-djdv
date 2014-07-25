from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
import sys


def errors404(request, template_name='404.html'):
	return render_to_response(template_name, locals(), context_instance=RequestContext(request))


def errors505(request, template_name='500.html'):
	exc_type, exc, trackback = sys.exc_info()
	return render_to_response(template_name, locals(), context_instance=RequestContext(request))


def errorview(request):
	raise Exception(_("Testing exception."))
