#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import urllib
import re
import uuid

import ystockquote

from input_methods import *


class Prices:
    """Class to store price developments."""
    numbers = {}

    def __init__(self, data):
        self.data = data
        self.secs = None
        self.numbers = {}
        all = self.data.c.execute('SELECT * FROM prices')
        # print('Preise initialisieren')
        for line in all.fetchall():
            id = line[1]
            date = line[2]
            price = line[3]
            if id not in self.numbers.keys():
                self.numbers[id] = {}
            self.numbers[id][date] = price

    def delete_prices(self, isin_id):
        stock_id = self.secs.get_stock_id_from_isin_id(isin_id)
        self.data.c.execute('''DELETE FROM prices WHERE stock_id = ?''', (stock_id, ))





    def row_exists(self, stock_id, date):
        result = self.data.c.execute('''SELECT price FROM prices WHERE stock_id = ? AND date = ?''',
                                     (stock_id, date)).fetchone()
        return False if result == None else True

    def update(self, isin_id, date, price, interactive=False, alt_name=''):
        # print('date for price update ', date)
        if not isin_id and interactive:
            print(self.secs)
            print('No valid ISIN given for', alt_name)
            tmp = input_string('Which stock is it?')
            tmp_stock = self.secs.find_stock(tmp, return_obj=True)
            isin_id = tmp_stock.isin_id
            tmp_stock.aliases.append(alt_name)
            self.secs.change_stock(isin_id, tmp_stock)
        elif not isin_id:
            print('No valid ISIN given.')
        if isin_id:
            id = self.secs.get_stock_id_from_isin_id(isin_id)
            if id not in self.numbers.keys():
                self.numbers[id] = {}
            self.numbers[id][date] = price
            if self.row_exists(id, date):
                self.data.c.execute('''UPDATE prices SET price = ? WHERE stock_id = ? AND date = ?''',
                                    (price, id, date))
            else:
                self.data.c.execute('''INSERT INTO prices(id, stock_id, date, price) VALUES (?, ?, ?, ?)''',
                                    (uuid.uuid4(), id, date, price))

    def get_price(self, stock_id, date, none_equals_zero=False):
        """Return price at given date or up to four days earlier"""
        price = None
        if none_equals_zero:
            price = 0.0
        for i in range(4):
            date = (datetime.datetime.strptime(date, '%Y-%m-%d') - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            try:
                price = self.numbers[stock_id][date]
            except:
                pass
        return price





    def __str__(self):
        keys = ['ID', 'Date', 'Price']
        x = PrettyTable(keys)
        x.align[keys[0]] = "l"  # Left align city names
        x.padding_width = 1  # One space between column edges and contents (default)
        for key in self.numbers.keys():
            for dates in self.numbers[key].keys():
                x.add_row((key, dates, self.numbers[key][dates]))
        return str(x)
