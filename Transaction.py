#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from prettytable import PrettyTable
import re
import datetime
import uuid

class Transaction:
	"""Class to store transactions"""
	def __init__(self, data, secs, portfolio):
		self.data = data
		self.secs = secs
		self.pf = portfolio
	def get_data_from_text(self, text):
		valid = False
		type = ''
		line_counter = 0
		lines = text.split('\n')
		print_all = False
		total_value = None
		currency = ''
		value = 0.0
		wert_found = False
		charge = 0.0
		while line_counter < len(lines):
			line = lines[line_counter]
			if (line.find('Daniel Dumke') != -1 or
				line.find('Daniel Stengel') != -1):
				valid = True
#				  print('Valid document for Daniel Dumke')
			if valid:
				if type == '':
					if line.find('DIVIDENDENGUTSCHRIFT ') != -1:
						type = 'dividende'
					elif line.find('ERTRAGSGUTSCHRIFT') != -1:
						type = 'dividende'
					elif line.find('WERTPAPIERABRECHNUNG') != -1:
#						  print_all = True
						line_counter += 1 
						line = lines[line_counter]
						if line.find('KAUF') != -1:
							type = 'kauf'
						elif line.find('VERKAUF') != -1:
							type = 'verkauf'
				else:
					if line.find('WKN') != -1:
#						  print(line)
						try:
							wkn = re.match('.*WKN.*([A-Z0-9]{6}).*', line).group(1)
						except:
							pass
						else:
#							  print(wkn)
							line_counter += 1 
							line = lines[line_counter]
							name = line.strip(' ')
					elif line.find('UMGER.ZUM DEV.-KURS') != -1:
						# Will be overwritten if WERT Line is found (and correct)
#						  print(line)
						result = re.match('UMGER.ZUM DEV.-KURS\s.*([A-Z]{3})\s*([0-9\.,]*)', line)
						currency = result.group(1)
						if currency != 'EUR':
							print('Error while importing, currency not EUR')
							sys.exit()
						value = float(result.group(2).replace('.','').replace(',','.'))
						wert_found = True
					elif line.find('WERT') != -1:
#						  print(line)
#						  pdb.set_trace()
						result = re.match('WERT\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4}).*([A-Z]{3})\s*([0-9\.,]*)', line)
						if not result:
							result = re.match('WERT\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})', line)
						date = datetime.datetime.strptime(result.group(1), "%d.%m.%Y").date()
						if currency == '':
							currency = result.group(2)
						if currency != 'EUR':
							print('Error while importing, currency not EUR')
							sys.exit()
						if value == 0.0:
							value = float(result.group(3).replace('.','').replace(',','.'))
							wert_found = True
#						  print(date, currency, value)					 
#						  print(result)

					elif line.find('Umsatz') != -1:
					# Nominale when buying
#						  print(line)
						line_counter += 1 
						line = lines[line_counter]
#						  print(line)
						nominale = float(line.replace(',','.'))
#						  print(nominale)
					elif line == 'Wertpapier':
					# Nominale when buying
#						  print(line)
						line_counter += 1 
						line = lines[line_counter]
						name = line.strip(' ')
						result = re.match('0,0.%.(.*?)00.*', name)
						if result:
							name = result.group(1).strip()
#						  print(name)
					
					elif re.match('AM.*([0-9\.]{10}).*UM.*', line) != None:
						date = re.match('AM.*([0-9\.]{10}).*UM.*', line).group(1)
						date = datetime.datetime.strptime(date, "%d.%m.%Y").date()
#						  print(date)
					elif line == 'Kurs':
					# Nominale when buying
#						  print(line)
						line_counter += 2
						line = lines[line_counter]
#						  print(line)										
						value = float(line.split(' ')[0].replace(',','.'))
#						  print(value)
						total_value = value * nominale
#						  print(total_value)
#						  print('total value ', total_value)
#						  print_all = True
					elif line.replace('.', '').find(str(total_value).replace('.',',')) != -1:
					# Nominale when buying
					# All additional lines
						while lines[line_counter+2] != '':
#							  print(line)
							line_counter += 1 
							line = lines[line_counter]
							charge += float(line.replace('.', '').replace(',', '.'))
#							  print(charge)
						line_counter += 1 
						line = lines[line_counter]
#						  print(line)
						total = float(line.replace('.', '').replace(',', '.'))
#						  print(total)
#						  print(total_value + charge, total)
#						  print(abs(total - (total_value + charge)))
#						  print(lines[line_counter+1])
#						  print(lines[line_counter+2])
#						  print(lines[line_counter+3])						  
						if abs(total - (total_value + charge)) > 0.01:
							print('Error while importing, totals do not match')
							sys.exit()
#						  print(line)
#			  if print_all:
#			  print(line.replace('.', ''))
			line_counter += 1 
		if not valid:
			return None
		elif type == 'dividende':
			return {'type': 'd', 'name': name, 'date': date, 'value': value}
		elif type == 'kauf':
			return {'type': 'b', 'name': name, 'date': date, 'nominale': nominale, 'value': value, 'cost': charge}	
		elif type == 'verkauf':
			return {'type': 's', 'name': name, 'date': date, 'nominale': nominale, 'value': value, 'cost': charge}	
	def add(self, type, stock_id, date, nominal, price, cost, portfolio):
		if stock_id != None:
			if price < 0:
				price = -1 * price
			if cost < 0:
				cost = -1 * cost
			if type == 'b':
				if nominal < 0:
					nominal = -1 * nominal
				total = -1 * price * nominal - cost
			elif type == 's':
				if nominal > 0:
					nominal = -1 * nominal
				total = -1 * price * nominal + cost
			elif type == 'd':
				if nominal != 0:
					price = price * nominal
					nominal = 0
				cost = 0
				total = price
			result = self.data.c.execute('''SELECT id FROM transactions WHERE type = ? AND portfolio = ? AND stock_id = ? AND date = ? AND nominal = ? AND price = ? AND cost = ? AND total = ?''', (type, portfolio, stock_id, date, nominal, price, cost, total)).fetchall()
            
			if result == []:
				self.data.c.execute('INSERT INTO transactions (id, type, portfolio, stock_id, date, nominal, price, cost, total) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (uuid.uuid4(), type, portfolio, stock_id, date, nominal, price, cost, total))
				print('Cash addition ' + str(total))
				self.pf.adjust_cash(portfolio, total)
				return True
			else:
				print('Transaction already seems to exist: ' + str(result))
				return True
		else:
			return False
#		  self.data.commit()
	def get_total_invest(self, portfolio, from_date, to_date):
		return self.get_total(portfolio, 'b', from_date, to_date)
	def get_total_divest(self, portfolio, from_date, to_date):
		return self.get_total(portfolio, 's', from_date, to_date)
	def get_total_dividend(self, portfolio, from_date, to_date):
		return self.get_total(portfolio, 'd', from_date, to_date)
	def get_total(self, portfolio, type, from_date, to_date):
		result = self.data.c.execute('''SELECT SUM(total) FROM transactions WHERE portfolio = ? AND type = ? AND date >= ? AND date <= ?''', (portfolio, type, from_date, to_date)).fetchall()
		if result != None:
			result = result[0]
			if result != None:
				result = result[0]
		if result == None:
			result = 0.0
		return result
	def get_portfolio(self, portfolio, date):
		"""Get portfolio contents on that specific date, incl. all transactions from that date"""
		result = self.data.c.execute("""SELECT stock_id, nominal FROM transactions WHERE portfolio = ? AND (type = 'b' OR type = 's') AND date <= ?""", (portfolio, date)).fetchall()
		stocks = {}
		for item in result:
			if item[0] not in stocks.keys():
				stocks[item[0]] = 0.0
			stocks[item[0]] = stocks[item[0]] + item[1]
		return stocks

	def get_total_for_portfolio(self, portfolio):
		result = self.data.c.execute('''SELECT name, SUM(nominal), SUM(cost), SUM(total) FROM transactions INNER JOIN stocks ON stocks.id = transactions.stock_id WHERE portfolio = ? GROUP BY stock_id''', (portfolio,)).fetchall()
# 		for item in result
		return result
	def __repr__(self):
		keys = ['Name', 'Type', 'Date', 'Total']
		result = self.data.c.execute('''SELECT stock_id, type, date, total FROM transactions ORDER BY date DESC''').fetchall()
		x = PrettyTable(keys)
		x.padding_width = 1 # One space between column edges and contents (default)
		for item in result:
			item = list(item)
			item[0] = self.secs.get_name_from_stock_id(item[0])
			x.add_row(item)
		return str(x)