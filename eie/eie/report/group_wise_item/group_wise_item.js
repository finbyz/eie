// Copyright (c) 2016, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Group Wise Item"] = {
	"filters": [
		{
			fieldname: "name",
			label: __("ID"),
			fieldtype: "Link",
			options: "Item"
		},
		{
			fieldname: "item_other_names",
			label: __("Item Other Names"),
			fieldtype: "Data"
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname: "owner",
			label: __("Created By"),
			fieldtype: "Link",
			options: "User"
		},
	]
}
