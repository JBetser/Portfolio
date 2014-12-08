from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from core.forms import PortfolioFormOneDate, PortfolioFormTwoDates, PortfolioFormStockTwoDates
from core.models import UI
from securities.models import Security
from transactions.models import Transaction
from money.models import Money
#from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
#from matplotlib.figure import Figure
#from matplotlib.dates import DateFormatter
#from matplotlib.ticker import ScalarFormatter
import datetime
from decimal import Decimal
from django.utils import timezone
from django.http import HttpResponse
from securities.models import Price
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.http import Http404
from django.shortcuts import render_to_response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
import random
import string
from django.shortcuts import redirect



from django.views.decorators.cache import cache_page
# Create your views here.

ui = UI()


def index(request):
    return render(request, 'index.html')



def stock_graph_png(request, security, from_date, to_date):
    s = Security()
    sec = s.find(security)
    fig=Figure()
    ax=fig.add_subplot(111)

    p = Price()
    dates, values = p.get_dates_and_prices(sec, from_date, to_date)
    ax.plot_date(dates, values, '-')
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    # import pdb; pdb.set_trace()
    ax.set_ylabel(sec.name)
    ax.set_xlabel('Date')
    canvas = FigureCanvas(fig)
    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response

def stock_graph(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = PortfolioFormStockTwoDates(request.POST)
        # check whether it's valid:
        if form.is_valid():
            content = 'Stock price development for shown timeframe'
            return render(request, 'stock_graph.html', {'block_title': 'Security Graph',
                                                                  'form': form,
                                                                  'content': content,
                                                                  'security': form.cleaned_data['security'],
                                                                  'from_date': form.cleaned_data['from_date'].strftime('%Y-%m-%d'),
                                                                  'to_date': form.cleaned_data['to_date'].strftime('%Y-%m-%d')})
    # if a GET (or any other method) we'll create a blank form
    else:
        form = PortfolioFormStockTwoDates()

    return render(request, 'stock_graph.html', {'block_title': 'Security Graph',
                                                          'form': form})

@login_required
def rolling_profitability(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = PortfolioFormTwoDates(request.POST)
        # check whether it's valid:
        if form.is_valid():
            dates, roi_list = ui.rolling_profitability(form.cleaned_data['from_date'],
                                                       form.cleaned_data['to_date'],
                                                       request.user)
            if dates:
                dates = list(map(lambda x: x.strftime("%b '%y"), dates))
                # print(roi_list)
                roi_list = list(map(lambda x: float(round(x, 2)), roi_list))
            # if roi_list == [0.0,]*13:
                # print(roi_list)
            return render(request, 'rolling_profitability.html', {'block_title': 'Rolling Profitability',
                                                                  'active_nav': '#nav_pf_rolling_profitability',
                                                                  'form': form,
                                                                  'from_date': form.cleaned_data['from_date'].strftime('%Y-%m-%d'),
                                                                  'to_date': form.cleaned_data['to_date'].strftime('%Y-%m-%d'),
                                                                  'dates': dates,
                                                                  'roi_list': roi_list,
                                                                  'username': request.user.username,})
    # if a GET (or any other method) we'll create a blank form
    else:
        form = PortfolioFormTwoDates()

    return render(request, 'rolling_profitability.html', {'block_title': 'Rolling Profitability',
                                                          'form': form,
                                                          'username': request.user.username,})

@login_required
def portfolio_development(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = PortfolioFormTwoDates(request.POST)
        # check whether it's valid:
        if form.is_valid():
            dates, pf_values, cash_values, income_values, invest_values, roi =\
                ui.portfolio_development(form.cleaned_data['from_date'],
                                         form.cleaned_data['to_date'],
                                         request.user)

            dates = list(map(lambda x: x.strftime("%b '%y"), dates))
            pf_values = list(map(lambda x: float(round(x/1000, 2)), pf_values))
            cash_values = list(map(lambda x: float(round(x/1000, 2)), cash_values))

            income_values['dates'] = list(map(lambda x: x.strftime("%b '%y"), income_values['dates']))

            income_values['income'] = list(map(lambda x: float(round(x/1000, 2)), income_values['income']))
            income_values['expense'] = list(map(lambda x: float(round(x/1000, 2)), income_values['expense']))

            invest_values['invest'] = list(map(lambda x: float(round(x/1000, 2)), invest_values['invest']))
            invest_values['divest'] = list(map(lambda x: float(round(x/1000, 2)), invest_values['divest']))
            invest_values['dividend'] = list(map(lambda x: float(round(x/1000, 2)), invest_values['dividend']))
            return render(request, 'portfolio_development.html', {'block_title': 'Portfolio Development',
                                                                  'active_nav': '#nav_pf_development',
                                                                  'form': form,
                                                                  'from_date': form.cleaned_data['from_date'],
                                                                  'to_date': form.cleaned_data['to_date'],
                                                                  'dates': dates,
                                                                  'pf_values': pf_values,
                                                                  'cash_values': cash_values,
                                                                  'income_values': income_values,
                                                                  'invest_values': invest_values,
                                                                  'roi': roi,
                                                                  'username': request.user.username,})
    # if a GET (or any other method) we'll create a blank form
    else:
        form = PortfolioFormTwoDates()
    return render(request, 'portfolio_development.html', {'block_title': 'Portfolio Development',
                                                'form': form,
                                                'username': request.user.username,})

def get_color_and_highlight(number=5):
    color = {'aqua': "#00ffff",
             'azure': "#f0ffff",
             'beige': "#f5f5dc",
             'black': "#000000",
             'blue': "#0000ff",
             'brown': "#a52a2a",
             'cyan': "#00ffff",
             'darkblue': "#00008b",
             'darkcyan': "#008b8b",
             'darkgrey': "#a9a9a9",
             'darkgreen': "#006400",
             'darkkhaki': "#bdb76b",
             'darkmagenta': "#8b008b",
             'darkolivegreen': "#556b2f",
             'darkorange': "#ff8c00",
             'darkorchid': "#9932cc",
             'darkred': "#8b0000",
             'darksalmon': "#e9967a",
             'darkviolet': "#9400d3",
             'fuchsia': "#ff00ff",
             'gold': "#ffd700",
             'green': "#008000",
             'indigo': "#4b0082",
             'khaki': "#f0e68c",
             'lightblue': "#add8e6",
             'lightcyan': "#e0ffff",
             'lightgreen': "#90ee90",
             'lightgrey': "#d3d3d3",
             'lightpink': "#ffb6c1",
             'lightyellow': "#ffffe0",
             'lime': "#00ff00",
             'magenta': "#ff00ff",
             'maroon': "#800000",
             'navy': "#000080",
             'olive': "#808000",
             'orange': "#ffa500",
             'pink': "#ffc0cb",
             'purple': "#800080",
             'violet': "#800080",
             'red': "#ff0000",
             'silver': "#c0c0c0",
             'white': "#ffffff",
             'yellow': "#ffff00"
    }
    complements = {'#8FB700': '#7FA700',
             '#6BE200': '#5BD200',
             '#C2F400': '#B2E400',
             '#FF9800': '#EF8800',
             '#CB8800': '#BB7800',
             'magenta': 'darkmagenta',
             'lime': 'darkolivegreen',
             'orange': 'darkorange',
             'orchid': 'darkorchid',
             'red': 'darkred',
             'salmon': 'darksalmon',
             'violet': 'darkviolet'}
    # to preserve order
    orig_colors = ['#8FB700', '#6BE200', '#C2F400', '#FF9800', '#CB8800']
    colors = []
    for i in range(number):
        colors.append(orig_colors[i % 5])
    # print(colors)
    result = []
    for normal_color in colors:
        highlight_color = complements[normal_color]
        result.append((normal_color, highlight_color))
    return result


@login_required
def new_invest(request):
    t = Transaction()
    # for item in Money.objects.all():
    #     item.user = User.objects.get(username='danst')
    #     item.save()
    # print(request.user)
    m = Money()
    today = timezone.now().date()
    portfolio_parts = t.get_total_per_type('All', today, request.user)
    wealth = m.get_wealth(today, request.user)
    content = list(portfolio_parts.items())
    content.append(('Cash', wealth))
    total = Decimal(0)
    for item in content:
        total += item[1]

    content = sorted(content, key=lambda x: x[0])

    result = []
    pie_colors = get_color_and_highlight()
    for num, item in enumerate(content):
        if total != 0:
            percentage = int(item[1]/total*100)
        else:
            percentage = 'n/a'
        result.append(item + (str(percentage)+'%',) + pie_colors[num])
    nav_total = total #* Decimal('0.85') # May deduction factor
    nav_content = result
    # print(result)
    return render(request, 'new_invest.html', {'block_title': 'Overview',
                                               'active_nav': '#nav_overview',
                                               'nav_content': nav_content,
                                               'nav_total': nav_total,
                                               'username': request.user.username,})


@login_required
def portfolio_overview(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = PortfolioFormTwoDates(request.user, request.POST)
        # check whether it's valid:
        if form.is_valid():
            t = Transaction()
            print(form.cleaned_data['from_date'], form.cleaned_data['to_date'])
            print(type(form.cleaned_data['from_date']), type(form.cleaned_data['to_date']))
            content = t.list_pf(form.cleaned_data['from_date'], form.cleaned_data['to_date'], request.user)
            pie_colors = get_color_and_highlight(len(content))
            result = []
            for num, item in enumerate(content):
                # print(pie_colors[num])
                item['color'] = pie_colors[num][0]
                item['highlight'] = pie_colors[num][1]
                # print(item)
                result.append(item)
            return render(request, 'portfolio_overview.html', {'block_title': 'Portfolio Overview',
                                                               'active_nav': '#nav_pf_overview',
                                                               'form': form,
                                                               'from_date': form.cleaned_data['from_date'],
                                                               'to_date': form.cleaned_data['to_date'],
                                                               'header': ['Name', 'Nominal', 'Price',
                                                                          'Last value', 'Dividends', 'Current value', 'Profit', 'ROI'],
                                                               'walk_through_header': ['name',
                                                                                       'nominal',
                                                                                       'price',
                                                                                       'value_at_beginning',
                                                                                       'dividends',
                                                                                       'value_at_end',
                                                                                       'profit', 'roi'],
                                                               'portfolio_content': result,
                                                               'username': request.user.username,})
    # if a GET (or any other method) we'll create a blank form
    else:
        form = PortfolioFormTwoDates(request.user)

    return render(request, 'portfolio_overview.html', {'block_title': 'Portfolio Overview',
                                                       'form': form,
                                                       'username': request.user.username,})



@login_required
def forecast_retirement(request):
    # import pdb; pdb.set_trace()
    m = Money()
    result_development = m.aggregate_results(request.user)
    print(result_development)
    for key in [2020, 2025, 2030]:
        result_development[key] = list(map(lambda x: float(round(x/1000, 2)), result_development[key]))
    now = timezone.now().date().year + 1
    dates = list(range(len(result_development[2020])))
    dates = [now+(item*5) if item % 1 == 0 else '' for item in dates]
    # print(dates)
    return render(request, 'forecast_retirement.html', {'block_title': 'Forecast retirement',
                                                        'active_nav': '#nav_forecast',
                                                        'development': result_development,
                                                        'dates': dates,
                                                        'username': request.user.username,})

def randomword(length):
   return ''.join(random.choice(string.ascii_lowercase) for i in range(length))

@login_required
def new_demo_user(request):

    if request.user.username == 'danst':
        result = {}
        t = Transaction()
        m = Money()
        user_exists = True
        try:
            User.objects.get(username='demo')
        except:
            user_exists = False
        # import pdb; pdb.set_trace()
        if user_exists:
            tmp = Transaction.objects.filter(user=User.objects.get(username='demo'))
            tmp.delete()
            tmp = Money.objects.filter(user=User.objects.get(username='demo'))
            tmp.delete()
            tmp = User.objects.get(username='demo')
            tmp.delete()
        user_name = 'demo'
        user_password = randomword(5)
        user_mail = 'demo@demo.me'
        result['name'] = user_name
        result['password'] = user_password
        result['mail'] = user_mail
        # result['factor'] = factor
        new_user = User.objects.create_user(user_name, user_mail, user_password)
        factor = Decimal(1/(random.randrange(10, 30)))
        t.copy_transactions_to_new_user(User.objects.get(username='danst'), new_user, factor)
        factor = Decimal(1/(random.randrange(10, 30)))
        m.copy_money_to_new_user(User.objects.get(username='danst'), new_user, factor)
    else:
        raise Http404

    return render(request, 'new_demo_user.html', {'block_title': 'Generated new Demo User',
                                                        'active_nav': '#nav_overview',
                                                        'result': result,
                                                        'username': request.user.username,})

@login_required
def login_demo(request, username, password):
    print('Hello')
    print(username, password)
    if username == 'demo':
        print('Ahoy')
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                logout(request)
                login(request, user)
                return redirect('new_invest')
            else:
                # Return a 'disabled account' error message
                print('Disabled account')
                pass
        else:
            # Return an 'invalid login' error message.
            print('invalid login')
            pass

@login_required
def recommendation(request):
    # if this is a POST request we need to process the form data
    # create a form instance and populate it with data from the request:
    ui = UI()
    best_five, worst_five = ui.recommendation(request.user)

    return render(request, 'recommendations.html', {'block_title': 'Recommendations',
                                                       'active_nav': '#nav_recommendations',
                                                       'best_five': best_five,
                                                       'worst_five': worst_five,
                                                       'header': ['Name', 'ROI'],
                                                       'username': request.user.username,})
# if a GET (or any other method) we'll create a blank form
