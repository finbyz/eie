# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.user import get_user_fullname

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data ,None

def get_columns():
	columns = [
		_("User Name") + ":Link/User:120",
		_("Document") + ":Int:100",
		_("Items") + ":Int:100",
	]
	return columns

def get_data(filters):
	
	doctype_list = ['Quotation', 'Sales Order', 'Sales Invoice', 'Purchase Invoice', 'Purchase Order', 'Delivery Note', 'Purchase Receipt']

	doctype = []

	if filters.doctype in doctype_list:
		doctype.append(filters.doctype)
	else:
		doctype = doctype_list[:]

	transaction_date = ['Quotation', 'Sales Order', 'Purchase Order']


	for doc in doctype:
		conditions = ''
		date = 'posting_date'
		if doc in transaction_date:
			date = 'transaction_date'

		if filters.date_range: conditions += " and {0} >= '{1}'".format(date, filters.date_range[0])
		# OUTPUT of conditions = " and transaction_date >= '2018-01-01'"
		if filters.date_range: conditions += " and {0} <= '{1}'".format(date, filters.date_range[1])
		# OUTPUT of conditions = " and transaction_date >= '2018-01-01' and transaction_date <= '2018-01-01'"
		if filters.user:conditions += " and owner = '{0}'".format(filters.user)
		# OUTPUT of conditions = " and transaction_date >= '2018-01-01' and transaction_date <= '2018-01-01' and owner = 'filters.user'"

		data = []
		
		dt = frappe.db.sql("""
			SELECT
				{date} as 'Date',name as 'ID' , owner as 'Created By'
			FROM
				`tab{doc}`
			WHERE
				docstatus < 2
				{conditions}
			ORDER BY
				modified DESC""".format(date=date, doc=doc, conditions=conditions), as_dict=1)

		d = dt[:]
		cnt = 0
	
		user_list = list(map(lambda u: u['Created By'] if 'Created By' in u else '', dt))
		user_item_list = list(map(lambda u: u['Owner'] if 'Owner' in u else '', dt))
		users = list(set(user_list))

		for row in d:	
			row["User Name"] = get_user_fullname(row['Created By'])
			row["Document"] = user_list.count(row['Created By'])
			cnt = insert_items(dt, row, doc, cnt)
			row["Items"] = cnt

			data += dt

	return data 	

def insert_items(data, row, doc, cnt):

	items = frappe.db.sql("""
		SELECT
			owner as 'Owner'
		FROM
			`tab{0} Item`
		WHERE
			parent = '{1}' """.format(doc, row['ID']), as_dict=1)

	for i in items[:]:
		# data.insert(cnt, {'Items': i["Owner"]})
		cnt +=1

	return cnt