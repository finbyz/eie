// Copyright (c) 2016, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["Item Price Comparison"] = {
	"filters": [
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"reqd": 1,
			"default": "TR GENERAL LAB EQUIPMENTS"
		},	
		{
		 	fieldname: "price_list1",
		 	label: __("Price List 1"),
		 	fieldtype: "Link",
		 	options: "Price List",
			"reqd": 1,
			"default": "Standard Buying"			
		},
		{
		 	fieldname: "price_list2",
		 	label: __("Price List 2"),
		 	fieldtype: "Link",
		 	options: "Price List",
			"reqd": 1,
			"default": "Standard Selling"			
		},
	]
}
