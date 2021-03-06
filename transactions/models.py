import uuid
from decimal import *

from django.db import models

from securities.models import Security
from securities.models import SecuritySplit
from securities.models import Price
from transactions.Importer import CortalConsors
from django.utils import timezone
import datetime
from django.contrib.auth.models import User
from transactions.validators import *

import jellyfish

# from django.core.exceptions import ValidationError

# Create your models here.
class Portfolio(models.Model):
    name = models.CharField(max_length=200)

    def find(self, name):
        """
        Find securities
        :param name_alias_id:
        :return: ISIN_ID based on any (useful) information
        """
        find_something = Portfolio.objects.get_or_create(name=name)[0]
        return find_something
    def __str__(self):
        return 'Model:PF:' + str(self.name)


class Transaction(models.Model):
    # id = models.CharField(max_length=100, blank=True, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(User, null=True, default=None)
    transaction_type = models.CharField(max_length=1)
    portfolio = models.ForeignKey(Portfolio)
    stock_id = models.ForeignKey(Security)
    date = models.DateField('date of transaction')
    nominal = models.DecimalField(max_digits=20, decimal_places=4)
    price = models.DecimalField(max_digits=20, decimal_places=4)
    cost = models.DecimalField(max_digits=20, decimal_places=4)
    total = models.DecimalField(max_digits=20, decimal_places=4)
    prices = Price()
    secs = Security()
    pf = Portfolio()

    def __str__(self):
        return ';'.join((
        str(self.portfolio), self.transaction_type, str(self.stock_id), str(self.date), str(self.nominal), str(self.price),
        str(self.cost), str(self.total)))

    def import_sources(self, path):
        i = CortalConsors()
        price_updates, transactions_update_pdf = i.read_pdfs(path)
        transaction_update_csv = i.read_old_depot_csv(path)
        transactions_update = transactions_update_pdf + transaction_update_csv
        output_transactions_updates = self.import_transactions(transactions_update)
        output_price_updates = self.prices.import_prices(price_updates)
        output_price_updates = sorted(output_price_updates, key=lambda x: x['name'])
        return {'prices': output_price_updates, 'transactions': output_transactions_updates}

    def import_transactions(self, transaction_update):
        output = []
        for trans in transaction_update:
            if trans:
                print('Adding transaction for', trans['name'])
                sec = self.secs.find(trans['name'])
                if not sec:
                    self.secs.add_stump(name=trans['name'], isin_id=trans['isin'])
                    sec = self.secs.find(trans['name'])
                    output.append({'name': trans['name'], 'status': 'Added stock'})
                elif sec and trans['isin']:
                    sec.isin_id = trans['isin']
                    sec.save()
                    print('Added ISIN')
                # Add price of transaction
                p = Price()
                p.add(sec, trans['date'], trans['value'])

                pf = self.pf.find('All')
                success = self.add(transaction_type=trans['type'],
                                   portfolio=pf,
                                   stock_id=sec,
                                   date=trans['date'],
                                   nominal=trans['nominal'],
                                   price=trans['value'],
                                   cost=trans['cost'])
                if success:
                    output.append(trans)
                else:
                    trans['status'] = 'Transaction already existed, no new transaction created'
                    output.append(trans)
        return output


    def add(self, transaction_type, portfolio, stock_id, date, nominal, price, cost):
        nominal = abs(nominal)
        price = abs(price)
        cost = abs(cost)
        if transaction_type == 'b':
            total = -(nominal * price) - cost
        elif transaction_type == 's':
            total = (nominal * price) - cost
        elif transaction_type == 'd':
            total = price
            nominal = Decimal(0)
            cost = Decimal(0)
        else:
            raise NameError('Not a valid transaction type (' + str(transaction_type) + ')')

        if not isinstance(date, datetime.datetime):
            now = timezone.now().date()
        else:
            now = timezone.now()
        if date > now:
            raise NameError('Date in the future (' + str(date) + ')')
        # import pdb; pdb.set_trace()
        t = Transaction.objects.filter(transaction_type=transaction_type,
                                       portfolio=portfolio,
                                       date=date,
                                       nominal=nominal,
                                       price=price)
        if t:
            return None
        else:
            t = Transaction.objects.create(transaction_type=transaction_type,
                                           portfolio=portfolio,
                                           stock_id=stock_id,
                                           date=date,
                                           nominal=nominal,
                                           price=price,
                                           cost=cost,
                                           total=total)
            return t

    def get_invest_divest(self, portfolio, stock_id, from_date, to_date):
        # print(type(from_date), type(to_date))
        in_divest = Decimal(0)
        in_divest = self.get_total(portfolio, 'b', from_date, to_date, stock_id)
        in_divest += self.get_total(portfolio, 's', from_date, to_date, stock_id)
        return in_divest

    def get_total_invest(self, portfolio, from_date, to_date):
        return self.get_total(portfolio, 'b', from_date, to_date)

    def get_total_divest(self, portfolio, from_date, to_date):
        return self.get_total(portfolio, 's', from_date, to_date)

    def get_total_dividend(self, portfolio, from_date, to_date, stock_id=None):
        return self.get_total(portfolio, 'd', from_date, to_date, stock_id)

    def get_total(self, portfolio, transaction_type, from_date, to_date, stock_id=None):
        """
        :param portfolio: Name of portfolio
        :param transaction_type: Types B uy, S ell, D ividend
        :param from_date: Starting date (excluding date mentioned)
        :param to_date: End date of analysis (including date mentioned)
        :param stock_id: Stock ID
        :return:
        """
        total = Decimal(0)
        if stock_id:
            for item in Transaction.objects.filter(portfolio__name=portfolio,
                                                   transaction_type=transaction_type,
                                                   date__gt=from_date,
                                                   date__lte=to_date,
                                                   stock_id=stock_id):
                total += item.total
        else:
            for item in Transaction.objects.filter(portfolio__name=portfolio,
                                                   transaction_type=transaction_type,
                                                   date__gt=from_date,
                                                   date__lte=to_date):
                total += item.total
        return total

    def get_total_per_type(self, portfolio, date, user):
        total = {}

        stocks = self.get_total_for_portfolio(portfolio, date, user)
        # print(stocks)
        for stock in stocks:
            if not stock.type in total.keys():
                total[stock.type] = Decimal(0)
            price = self.prices.get_last_price_from_stock_id(stock, date)
            total[stock.type] += abs(stocks[stock]['nominal'] * price)
        return total


    def get_stocks_in_portfolio(self, portfolio, date):
        """Get portfolio contents on that specific date, incl. all transactions from that date"""
        result = Transaction.objects.filter(portfolio__name=portfolio,
                                            transaction_type='b',
                                            date__lte=date) |\
                 Transaction.objects.filter(portfolio__name=portfolio,
                                            transaction_type='s',
                                            date__lte=date)
        stocks = {}
        for item in result:
            if item.id not in stocks.keys():
                stocks[item.id] = Decimal(0)
            stocks[item.id] = stocks[item.id] + item.nominal
        return stocks

    def rectify_nominal_with_stock_split(self, stock_id, stock_date, nominal):
        ss = SecuritySplit()
        splits = ss.get_splits(stock_id)
        if splits:
            for split in splits:
                if stock_date < split.date:
                    nominal = nominal * split.ratio
        return nominal

    def get_total_for_portfolio(self, portfolio, date, user):
        result = Transaction.objects.filter(portfolio__name=portfolio, date__lte=date, user=user)
        per_stock = {}
        for item in result:
            sign = 1
            if item.transaction_type == 's':
                sign = -1
            if item.stock_id not in per_stock.keys():
                per_stock[item.stock_id] = {'nominal': sign * self.rectify_nominal_with_stock_split(item.stock_id,
                                                                                             item.date,
                                                                                             item.nominal),
                                            'cost': item.cost,
                                            'total': item.total}
            else:
                per_stock[item.stock_id]['nominal'] += sign * self.rectify_nominal_with_stock_split(item.stock_id,
                                                                                             item.date,
                                                                                             item.nominal)
                per_stock[item.stock_id]['cost'] += item.cost
                per_stock[item.stock_id]['total'] += item.total
        # Remove securities with zero nominale
        for key, value in per_stock.copy().items():
            if value['nominal'] == 0:
                del per_stock[key]
        return per_stock

    def list_pf(self, from_date, to_date, user, portfolio='All'):
        """ Portfolio Overview function table of all stocks and profits since from_date
        :param portfolio: xxx
        :param from_date: When to start
        :param to_date: When to end
        :return:
        """
        # print(from_date, to_date)
        # Temporary update all old prices from transaction data
        # for trans in Transaction.objects.all():
        #     # Add price of transaction
        #     if trans.transaction_type != 'd':
        #         print(trans.stock_id, trans.date, trans.price)
        #         p = Price()
        #         p.add(trans.stock_id, trans.date, trans.price)
        stock_at_beginning = self.get_total_for_portfolio(portfolio, from_date, user)
        stocks_at_end = self.get_total_for_portfolio(portfolio, to_date, user)
        values = []
        total_value = Decimal(0)
        total_value_at_beginning = Decimal(0)
        total_profit = Decimal(0)
        total_dividends = Decimal(0)
        # import pdb; pdb.set_trace()
        for stock_id in sorted(stocks_at_end.keys(), key=lambda x: x.name.lower()):

            price_at_beginning = self.prices.get_last_price_from_stock_id(stock_id,
                                                                          from_date,
                                                                          none_equals_oldest_available=True)
            price_at_end = self.prices.get_last_price_from_stock_id(stock_id,
                                                                    to_date)
            # print('Stock', stock_id)
            # print(price_at_beginning, price_at_end)

            value_at_beginning = Decimal(0)
            value_at_end = Decimal(0)


            # print('Invest', self.get_invest_divest(portfolio, stock_id, from_date, to_date))
            if price_at_beginning:
                # print('Price', price_at_beginning)
                if stock_id in stock_at_beginning.keys():
                    # print('Nom', stock_at_beginning[stock_id]['nominal'])
                    # print('Price and already existing')

                    value_at_beginning = stock_at_beginning[stock_id]['nominal'] * price_at_beginning -\
                                         self.get_invest_divest(portfolio, stock_id, from_date, to_date)
                else:
                    value_at_beginning -= self.get_invest_divest(portfolio, stock_id, from_date, to_date)
                    # print('Price but not yet existed')
            else:
                # print('No price')
                value_at_beginning -= self.get_invest_divest(portfolio, stock_id, datetime.date(1900, 1, 1), from_date)



            # Calculate dividends
            dividends = self.get_total_dividend(portfolio, from_date, to_date, stock_id)
            # Calculate Value at end
            if price_at_end:
                # print(stocks_at_end[stock_id]['nominal'], price_at_end)
                value_at_end = stocks_at_end[stock_id]['nominal'] * price_at_end
            else:
                # print('No price', stocks_at_end[stock_id]['nominal'], price_at_end)
                pass
            # Calculate profit
            profit = value_at_end - value_at_beginning + dividends
            try:
                roi = str(round(profit/value_at_beginning * 100, 1)) + '%'
            except:
                roi = 'n/a'
            values.append({'stock_id': stock_id.id,
                           'name': stock_id.name,
                           'nominal': stocks_at_end[stock_id]['nominal'],
                           'cost': stocks_at_end[stock_id]['cost'],
                           'price': price_at_end,
                           'value_at_beginning': value_at_beginning,
                           'value_at_end': value_at_end,
                           'dividends': dividends,
                           'profit': profit,
                           'roi': roi})
            total_value_at_beginning += value_at_beginning
            total_value += value_at_end
            total_dividends += dividends
            total_profit += profit
        try:
            total_roi = str(round(((total_value-total_value_at_beginning)/total_value_at_beginning * 100), 1)) + '%'
        except:
            total_roi = 'n/a'
        values.append({'name': 'Total',
                       'value_at_beginning': total_value_at_beginning,
                       'dividends': total_dividends,
                       'value_at_end': total_value,
                       'profit': total_profit,
                       'roi': total_roi})
        return values

    def get_roi(self, from_date, to_date, user, portfolio='All'):
        result = self.list_pf(from_date, to_date, user, portfolio)
        roi = result[-1]['roi'][:-1]
        if roi != 'n/':
            result = Decimal(roi)/Decimal(100)
        else:
            result = Decimal(0)
        return result


    def get_pf_value(self, to_date, user, portfolio='All'):
        result = self.list_pf(to_date, to_date, user, portfolio)
        return result[-1]['value_at_end']

    def copy_transactions_to_new_user(self, old_user, new_user, factor):
        old_transactions = Transaction.objects.filter(user=old_user)
        for trans in old_transactions:
            trans.nominal = int(trans.nominal * factor)
            if trans.nominal > 0:
                trans.id = None
                trans.user = new_user

                trans.cost *= int(factor)
                if trans.type == 'b':
                    trans.total = -trans.nominal * trans.price - trans.cost
                elif trans.type == 's':
                    trans.total = trans.nominal * trans.price - trans.cost
                else:
                    trans.total *= factor
                trans.save()