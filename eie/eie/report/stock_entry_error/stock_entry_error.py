# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, db

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data()
	return columns, data
	
	
def get_columns():
	columns = [
		_("Stock Entry") + ":Link/Stock Entry:120",
		_("Item Code") + ":Link/Item:190",
		_("Serial No") + ":Link/Serial No:190",
		#_("Has Serial No") + ":Check:80",
	]
	return columns

		
def get_data():

	data = db.sql("""
			select
				sed.item_code as 'Item Code', sed.serial_no as 'Serial No', sed.parent as 'Stock Entry'
			from
				`tabStock Entry Detail` as sed
			join `tabItem` as i
			on sed.item_code = i.name
			where 
				sed.serial_no is null and i.has_serial_no = 1 and sed.docstatus < 2
			""", as_dict=1)
			
	return data