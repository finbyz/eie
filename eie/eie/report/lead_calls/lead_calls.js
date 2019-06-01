// Copyright (c) 2016, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Lead Calls"] = {
	"filters": [
		{
			fieldname: "user",
			label: __("User"),
			fieldtype: "Link",
			options: "User"
		},	
		{
			fieldname: "lead",
			label: __("Lead"),
			fieldtype: "Link",
			options: "Lead"
		},
		{
			fieldname: "from_date",
			label:__("From Date"),
			fieldtype: "Date",
			default : frappe.datetime.add_days(frappe.datetime.nowdate(), -30)
		},
		{
			fieldname: "to_date",
			label:__("To Date"),
			fieldtype: "Date",
			default : frappe.datetime.nowdate()
		}
	]	
}
