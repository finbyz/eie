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
		{
			"fieldname": "name",
			"label": _("Work Order"),
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 120
		},
		{
			"fieldname": "bom_no",
			"label": _("BOM"),
			"fieldtype": "Link",
			"options": "BOM",
			"width": 150
		},
		{
			"fieldname": "production_item",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 210
		},
		{
			"fieldname": "qty",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "produced_qty",
			"label": _("Manufactured Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "bom_rate",
			"label": _("Bom Rate"),
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"fieldname": "manufacturing_rate",
			"label": _("Manufacturing Rate"),
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"fieldname": "selling_rate",
			"label": _("Selling Rate"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "assign_person_name",
			"label": _("Assigned Person Name"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "planned_start_date",
			"label": _("Start Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "owner",
			"label": _("Created By"),
			"fieldtype": "Data",
			"width": 120
		},
	]
	return columns

def get_data(filters):
	conditions = get_conditions(filters)
	data = frappe.db.sql("""
		select wo.name, wo.production_item, wo.bom_no, wo.qty, wo.produced_qty, wo.planned_start_date, wo.owner, wo.status,
		wo.assign_to, bom.per_unit_cost as bom_rate, e.employee_name as assign_person_name, ip.price_list_rate as selling_rate,
		(sum(sed.valuation_rate*sed.qty)/sum(sed.qty)) as manufacturing_rate, se.posting_date
		from `tabWork Order` as wo 
		left join `tabBOM` as bom on bom.name = wo.bom_no 
		left join `tabEmployee` as e on wo.assign_to = e.name
		left join `tabItem Price` as ip on wo.production_item = ip.item_code
		left join `tabStock Entry` as se on wo.name = se.work_order
		left join `tabStock Entry Detail` as sed on sed.parent = se.name
		where wo.status != 'Cancelled' and ip.price_list = "Standard Selling" and se.stock_entry_type = "Manufacture" and sed.item_code = wo.production_item and se.docstatus = 1
		{conditions}
		group by wo.name
	""".format(conditions=conditions),as_dict=1)
	return data

def get_conditions(filters):
	
	conditions = ""

	conditions += filters.get('name') and " AND wo.name = '%s' " % filters.get('name') or ""
	conditions += filters.get('bom_no') and " AND wo.bom_no = '%s' " % filters.get('bom_no') or ""
	conditions += filters.get('production_item') and " AND wo.production_item = '%s' " % (filters.get('production_item')) or ""
	if filters.get('from_date'):
		
		conditions += " AND se.posting_date >= '%s'" % filters.get('from_date')
		#frappe.msgprint(str(" AND wo.planned_start_date >= '%s'" % filters.get('from_date')))
	
	if filters.get('to_date'):
		conditions += " AND se.posting_date <= '%s'" % filters.get('to_date')
	
	return conditions