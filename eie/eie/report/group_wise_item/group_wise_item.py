# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	columns = [
		_("Item") + ":Link/Item:140",
		_("Variant Of") + ":Link/Item:120",
		_("Maintain Stock") + ":Check:100",
		_("Has Serial No") + ":Check:90",
		_("Serial No Series") + ":Data:100",
		_("Item Group") + ":Link/Item Group:140",
		_("Template") + ":Check:70",
		_("Created By") + "::140",
		_("Created On") + "::140",
	]
	return columns

def get_data(filters):

	conditions = get_contitions(filters)

	data = frappe.db.sql("""
		SELECT
			name as 'Item', variant_of as 'Variant Of', is_stock_item as 'Maintain Stock', has_serial_no as 'Has Serial No', serial_no_series as 'Serial No Series', item_group as 'Item Group', has_variants as 'Template', owner as 'Created By', creation as 'Created On'
		FROM
			`tabItem`
		WHERE
			docstatus = 0
			{conditions} 
		ORDER BY
			item_name""".format(conditions=conditions), as_dict=1)

	return data
	
def get_contitions(filters):
	
	conditions = ''
	
	conditions += filters.name and ' and name = "%s"' %\
	 filters.name.replace("'","/'") or ''
	conditions += filters.item_other_names and ' and item_other_names = "%s"' %\
	 filters.item_other_names.replace("'","/'") or ''
	conditions += filters.owner and ' and owner = "%s"' %\
	 filters.owner.replace("'","/'") or ''

 	if filters.item_group:
	 	item_group = get_item_group_list(filters.item_group.replace("'","/'"))
		conditions += filters.item_group and " and item_group IN ('%s')" %\
		 "','".join(item_group) or ''

	return conditions

def get_item_group_list(item_group):

	item_group_list = [item_group]
	group = [item_group]
	is_group = frappe.db.get_value("Item Group", item_group, "is_group")
	
	loop = False
	
	if is_group:
		loop = True
	
	while loop:
		item_group_name = list()

		for g in group:
			item_list = frappe.db.get_values('Item Group',{"parent_item_group": g}, ["item_group_name", "is_group"], as_dict=1)
			
			for item in item_list:
				item_group_list.append(item["item_group_name"])

				if item["is_group"]:
					item_group_name.append(item["item_group_name"])
		
		if item_group_name:
			group = item_group_name
		else:
			loop = False

	return item_group_list