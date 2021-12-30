# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe import _
import string
import re


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data
	

def get_columns():
	columns = [
		{"label": _("Item"), "fieldname": "Item Code", "fieldtype": "Link", "options": "Item", "width": 500},
		{"label": _("Price 1"), "fieldname": "Price 1", "fieldtype": "Currency", "width": 90, "convertible": "rate", "options": "currency"},
		{"label": _("Price 2"), "fieldname": "Price 2", "fieldtype": "Currency", "width": 90, "convertible": "rate", "options": "currency"},
		{"label": _("Item Group"), "fieldname": "Item Group", "fieldtype": "Link", "options": "Item Group", "width": 300},
		{"label": _("Difference"), "fieldname": "Difference", "fieldtype": "Currency", "width": 90, "convertible": "rate", "options": "currency"},
		{"label": _("Price1 %"), "fieldname": "Price1 %", "fieldtype": "Currency", "width": 90, "convertible": "rate", "options": "currency"},
		{"label": _("Price2 %"), "fieldname": "Price2 %", "fieldtype": "Currency", "width": 90, "convertible": "rate", "options": "currency"}
	]
	return columns

def get_data(filters):
	conditions = get_conditions(filters)
	
	items=[]
	data = []
	price_list1=filters.get('price_list1')
	price_list2=filters.get('price_list2')
	
	items = frappe.db.sql("""
		SELECT item_code , item_group
		FROM `tabItem` 
		WHERE is_sales_item=1%s
		ORDER BY item_code ASC
		"""%conditions,as_dict=1)

	for item in items:
		row = {}
		row["Item Code"]=item.item_code
		row["Price 1"]=frappe.db.get_value("Item Price", {"price_list":price_list1,"item_code":item.item_code},"price_list_rate")
		row["Price 2"]=frappe.db.get_value("Item Price", {"price_list":price_list2,"item_code":item.item_code},"price_list_rate")
		row["Item Group"] = item.item_group
		if row["Price 1"] and row["Price 2"]:
			row["Difference"] = row["Price 2"]-row["Price 1"]
			row["Price1 %"]= str(round((row["Difference"])*100/row["Price 1"],2)) + '%'
			row["Price2 %"]= str(round((row["Difference"])*100/row["Price 2"],2)) + '%'
		else:
			row["Difference"] = 0
			row["Price1 %"]= str(0) + '%'
			row["Price2 %"]= str(0) + '%'
		data.append(row)				

	return data




def get_conditions(filters):
	
	conditions = ""

	conditions += filters.get('item_group') and " AND item_group = '%s' " % filters.get('item_group')
	return conditions	

