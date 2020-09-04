// Copyright (c) 2016, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Work Order Status"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1,
			"width": "40px"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "40px"
		},
		{
			'fieldname': 'name',
			'label': __("Work Order"),
			'fieldtype': 'Link',
			'options': 'Work Order'
		},
		{
			'fieldname': 'bom_no',
			'label': __("BOM"),
			'fieldtype': 'Link',
			'options': 'BOM'
		},
		{
			'fieldname': 'production_item',
			'label': __("Item"),
			'fieldtype': 'Link',
			'options': 'Item'
		},

	]
};
