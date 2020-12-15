// Copyright (c) 2016, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Stock Ageing EIE"] = {
		"filters": [
			{
				"fieldname":"company",
				"label": __("Company"),
				"fieldtype": "Link",
				"options": "Company",
				"default": frappe.defaults.get_user_default("Company"),
				"reqd": 1
			},
			{
				"fieldname":"to_date",
				"label": __("As On Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.get_today(),
				"reqd": 1
			},
			{
				"fieldname":"warehouse",
				"label": __("Warehouse"),
				"fieldtype": "Link",
				"options": "Warehouse"
			},
			{
				"fieldname":"item_code",
				"label": __("Item"),
				"fieldtype": "Link",
				"options": "Item"
			},
			{
				"fieldname":"brand",
				"label": __("Brand"),
				"fieldtype": "Link",
				"options": "Brand"
			},
			{
				"fieldname":"show_warehouse_wise_stock",
				"label": __("Show Warehouse-wise Stock"),
				"fieldtype": "Check",
				"default":true,
				"reqd":1
			}
		]
};
