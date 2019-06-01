// Copyright (c) 2016, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Lead Data"] = {
	"filters": [
		{
			fieldname: "state",
			label:__("State"),
			fieldtype: "Data",
			default : "Gujarat",
			reqd: 1
		},
		{
			fieldname: "name",
			label:__("Lead Name"),
			fieldtype: "Link",
			options: "Lead"
		}
	]
}
