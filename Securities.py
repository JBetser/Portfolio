#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from prettytable import PrettyTable
import string
import uuid

def normalize(s):
	for p in string.punctuation:
		s = s.replace(p, '')
	return s.lower().strip() 
		
class Security:
	"""Class for stocks, bond, cash, everything is a security."""
	def __init__(self, name, aliases, isin_id, yahoo_id, type):
		self.name = name
		if isin_id == None:
			isin_id = ''
		self.isin_id = isin_id
		if yahoo_id == None:
			yahoo_id = ''
		self.yahoo_id = yahoo_id
		self.type = type
		if aliases == None:
			self.aliases = []
		else:
			self.aliases = aliases
		self.keys = ['Name', 'Aliases', 'ISIN', 'Yahoo-ID', 'Type']
	def list(self):
		return (self.name, ', '.join(self.aliases), self.isin_id, self.yahoo_id, self.type)
	def __str__(self):
		x = PrettyTable(self.keys)
		x.align[self.keys[0]] = "l" # Left align city names
		x.padding_width = 1 # One space between column edges and contents (default)
		x.add_row(self.list())
		return str(x)

class Securities:
	"""Wrapper for all stored securities"""
	keys = ['Name', 'Aliases', 'ISIN', 'Yahoo ID', 'Type', 'Last price']
	def __init__(self, data):
		self.data = data
		self.securities = []
		all = self.data.c.execute('SELECT name, aliases, isin_id, yahoo_id, type FROM stocks')
		for line in all.fetchall():
			line = list(line)
#			  print(line)
			if line[1] != None:
				line[1] = line[1].split('::')
			self.securities.append(Security(*line))
		self.prices = None

	def add(self, name, aliases, isin_id, yahoo_id, type):
#		  print(aliases)
		already_exists = False
		for sec in self.securities:
			if (normalize(sec.isin_id) == normalize(isin_id)
				and normalize(isin_id)[:7] != normalize('unknown')):
				already_exists = True
				break
		if not already_exists:
			self.securities.append(Security(name, aliases, isin_id, yahoo_id, type))
			self.data.c.execute('INSERT INTO stocks(id, name, aliases, isin_id, yahoo_id, type) VALUES (?, ?, ?, ?, ?, ?)', (uuid.uuid4(), name, '::'.join(aliases), isin_id, yahoo_id, type))
		else:
			print('ID for Stock already exists, therefore not added')
	def change_stock(self, isin_id, sec):
		found = False
		for num, item in enumerate(self.securities):
			if isin_id.lower() in item.isin_id.lower():
				found = True
				self.securities[num] = sec
#				print('UPDATE stocks set name = ?, aliases = ?, isin_id = ?, yahoo_id = ?, type = ? WHERE isin_id = ?', (sec.name, '::'.join(sec.aliases), isin_id, sec.yahoo_id, sec.type, isin_id))
				self.data.c.execute('UPDATE stocks set name = ?, aliases = ?, isin_id = ?, yahoo_id = ?, type = ? WHERE isin_id = ?', (sec.name, '::'.join(sec.aliases), isin_id, sec.yahoo_id, sec.type, isin_id))
				self.data.commit()
				break
		return found
	def delete_stock(self, isin_id):
		found = False
		for num, item in enumerate(self.securities):
			if isin_id.lower() in item.isin_id.lower():
				found = True
				tmp = self.securities.pop(num)
				self.data.c.execute('DELETE FROM stocks WHERE isin_id = ? AND name = ?', (isin_id, tmp.name))
				break
		return found	  
#		  pickle.dump( self.securities, open( "securities.p", "wb" ) )
	def empty(self):
		return False if len(self.securities) > 0 else True
	def get_name_from_stock_id(self, stock_id):
		name = self.data.c.execute('''SELECT name FROM stocks WHERE id = ?''', (stock_id,)).fetchone()
		return None if name is None else name[0]
	def get_isin_id_from_stock_id(self, stock_id):
		name = self.data.c.execute('''SELECT isin_id FROM stocks WHERE id = ?''', (stock_id,)).fetchone()
		return None if name is None else name[0]


	def __str__(self):
		x = PrettyTable(self.keys)
		x.align[self.keys[0]] = "l" # Left align city names
		x.padding_width = 1 # One space between column edges and contents (default)
		for i in self.securities:
# 			print(i.isin_id, self.prices.get_last_price(i.isin_id))
			x.add_row(i.list() + (self.prices.get_last_price(i.isin_id),))
		return str(x)
	def __iter__(self):
		for x in self.securities:
			yield x
	def find_stock(self, stock_id_or_name, return_obj=False):
		found = None
		found_obj = None
		for item in self.securities:
			if (normalize(stock_id_or_name) in normalize(item.name) or
				normalize(stock_id_or_name) in normalize(item.isin_id)):
				found = item.isin_id
				found_obj = item
				break
			else:
				for alias in item.aliases:
					if normalize(stock_id_or_name) == normalize(alias):
						found = item.isin_id
						found_obj = item
						break						 
		if return_obj:
			return found_obj
		else:
			return found
	def get_stock_id_from_isin_id(self, isin_id):
		stock_id = self.data.c.execute('''SELECT id FROM stocks WHERE isin_id = ?''', (isin_id,)).fetchone()
		return None if stock_id is None else stock_id[0]