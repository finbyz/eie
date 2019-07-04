// Copyright (c) 2016, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Industry Contact"] = {
	"filters": [
		{
			fieldname: 'industry',
			label: __("Industry"),
			fieldtype: "Link",
			options: "Industry Type",
			default: "GENERAL",
		},
		{
			fieldname: 'has_email',
			label: __("Has Email"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: 'has_phone_no',
			label: __("Has Phone No"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: 'has_mobile_no',
			label: __("Has Mobile No"),
			fieldtype: "Check",
			default: 0,
		},
	]
}
