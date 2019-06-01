# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, db


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data()
	return columns,data

def get_columns():
	columns = [
		_("Item Code") + ":Link/Item:100",
		_("Purchase Order") + ":Link/Purchase Order:100",
	]

	return columns

def get_data():

	data_purchase_order = db.sql("""
		SELECT 
			poi.item_code as 'Item Code', poi.parent as 'Purchase Order'
		FROM
			`tabPurchase Order` as po inner join `tabPurchase Order Item` as poi ON (po.name = poi.parent)
		WHERE 
			 poi.item_code in (SELECT pb.new_item_code FROM `tabProduct Bundle` as pb)""" , as_dict=1)

	return data_purchase_order


	





