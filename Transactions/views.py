from django.http import HttpResponse

from Transactions.models import Transaction

# Create your views here.

def test(request):
    # import pdb; pdb.set_trace()
    t = Transaction()
    return HttpResponse("Hello, world. You're at the Transactions Test." + str(t.get_total_for_portfolio('All')[0]))


def update(request):
    # import pdb; pdb.set_trace()
    t = Transaction()
    t.import_sources()
    return HttpResponse("Hello, world. We are updating the prices.")