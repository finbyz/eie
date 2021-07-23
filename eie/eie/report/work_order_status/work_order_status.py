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
			"fieldname": "planned_start_date",
			"label": _("Start Date"),
			"fieldtype": "Date",
			"width": 100
		},
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
			"fieldname": "total_operational_cost",
			"label": _("Total Operational Cost"),
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"fieldname": "actual_manufacturing_cost",
			"label": _("Actual Manufacturing cost"),
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"fieldname": "total_manufacturing_cost",
			"label": _("Total Manufacturing Amount"),
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"fieldname": "actual_start_date",
			"label": _("Actual Start Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "actual_end_date",
			"label": _("Actual End Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "days_taken",
			"label": _("Days taken for production"),
			"fieldtype": "Int",
			"width": 50
		},
		{
			"fieldname": "raw_material_cost",
			"label": _("Raw Material Cost"),
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"fieldname": "grand_total_cost",
			"label": _("Grand Total Cost"),
			"fieldtype": "Currency",
			"width": 80
		},
		{
			"fieldname": "grand_total_final",
			"label": _("Grand Total Final"),
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
			"fieldname": "total_selling",
			"label": _("Total Selling"),
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
			"fieldname": "assigned_person_name_for_qc",
			"label": _("Assigned Person Name for QC"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "production_planning_manager_name",
			"label": _("Production Planning Manager"),
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
			"fieldname": "drawing_available",
			"label": _("Drawing Available"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "whether",
			"label": _("Whether"),
			"fieldtype": "Data",
			"width": 80
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
		select wo.name, wo.production_item, wo.bom_no, wo.qty, wo.produced_qty, wo.planned_start_date, wo.owner, wo.status, wo.actual_start_date, wo.actual_end_date, datediff(wo.actual_end_date,wo.actual_start_date)+1 as days_taken, wo.assigned_person_name_for_qc, wo.whether, wo.production_planning_manager_name, wo.drawing_available,
		wo.assign_to, bom.total_operational_cost,bom.per_unit_cost as bom_rate, bom.raw_material_cost, bom.grand_total_cost, (wo.produced_qty*bom.grand_total_cost) as grand_total_final , (wo.produced_qty* ip.price_list_rate) as total_selling ,e.employee_name as assign_person_name, (ip.price_list_rate) as selling_rate,
		(sum(sed.valuation_rate*sed.qty)/sum(sed.qty)) as manufacturing_rate, se.posting_date, ((sum(sed.valuation_rate*sed.qty)/sum(sed.qty)) + bom.total_operational_cost) as actual_manufacturing_cost,
		(((sum(sed.valuation_rate*sed.qty)/sum(sed.qty)) + bom.total_operational_cost) * wo.produced_qty) as total_manufacturing_cost

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