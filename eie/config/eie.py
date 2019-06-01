from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Courier"),
			"items": [
				{
					"type": "doctype",
					"name": "Outward Tracking",
				},
				{
					"type": "doctype",
					"name": "Courier Agency",
				},
				{
					"type": "doctype",
					"name": "Courier Company",
				},
				{
					"type": "doctype",
					"name": "Courier Items",
				},
				{
					"type": "doctype",
					"name": "Courier Item List",
				},
				{
					"type": "doctype",
					"name": "Transporter",
				},

			]
		},
		{
			"label": _("Term"),
			"items": [
				{
					"type": "doctype",
					"name": "Terms Detail"
				},
				{
					"type": "doctype",
					"name": "Terms Value"
				},
			]
		},
		{
			"label": _("Other"),
			"items": [
				{
					"type": "doctype",
					"name": "Specification"
				},
				{
					"type": "doctype",
					"name": "LUT Detail"
				},
				{
					"type": "doctype",
					"name": "Meeting Schedule"
				},
				{
					"type": "doctype",
					"name": "Meetings"
				},
				{
					"type": "doctype",
					"name": "Item Tax Updater"
				},
				{
					"type": "doctype",
					"name": "Employee Feedback"
				},
				
			]
		},
		{
			"label": _("Reports"),
			"items": [
				{
					"type": "report",
					"name": "EIE Ordered Items To Be Delivered",
					"doctype": "Sales Order",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Group Wise Item",
					"doctype": "Item",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Lead Calls",
					"doctype": "Lead",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Quotation Analysis",
					"doctype": "Quotation",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Sales Comments",
					"doctype": "Communication",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "EIE Eway Bill",
					"doctype": "Delivery Note",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "BOM with Selling Price",
					"doctype": "BOM",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "EIE GST HSN Sales Register",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Pending Issue",
					"doctype": "Issue",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "EIE GST Itemised Sales Register",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "EIE Item-wise Sales Register",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "EIE GSTR-1",
					"doctype": "GL Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "L&T Accounts Receivable",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "EIE Requested Items To Be Ordered",
					"doctype": "Purchase Order",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "EIE Requested Items To Be Ordered",
					"doctype": "Purchase Order",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Item Price Comparison",
					"doctype": "Item Price",
					"is_query_report": True
				},

			]
		}
	]