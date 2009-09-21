from django.template import Context, loader
from fogmachine.library.models import Host, Guest
from django.http import HttpResponse

def list(request):
    hosts = Host.objects.all().order_by('cobbler_name')
    t = loader.get_template('library/list.html')
    c = Context({
        'hosts': hosts,
    })
    return HttpResponse(t.render(c))

def checkout(request, host):
    return "checkout not implemented"

# Create your views here.
