# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _, msgprint


def execute(filters=None):
	columns = get_columns() 
	data = get_data(filters)
	return columns, data

def get_columns():
	columns = [
		{ "label": _("Lead"),"fieldname": "Lead","fieldtype": "Link","options":"Lead","width": 100},
		{ "label": _("Name"),"fieldname": "Name","fieldtype": "Data","width": 120},
		{ "label": _("Company Name"),"fieldname": "Company Name","fieldtype": "Data","width": 120},
		{ "label": _("Status"),"fieldname": "Status","fieldtype": "Data","width": 80},
		{ "label": _("Address Line 1"),"fieldname": "Address Line 1","fieldtype": "Data","width": 100},
		{ "label": _("Address Line 2"),"fieldname": "Address Line 2","fieldtype": "Data","width": 100},
		{ "label": _("State"),"fieldname": "State","fieldtype": "Data","width": 100},
		{ "label": _("City"),"fieldname": "City","fieldtype": "Data","width": 100},
		{ "label": _("Pincode"),"fieldname": "Pincode","fieldtype": "Data","width": 70},
		{ "label": _("Country"),"fieldname": "Country","fieldtype": "Data","width": 100},
		{ "label": _("Phone"),"fieldname": "Phone","fieldtype": "Data","width": 100},
		{ "label": _("Mobile No"),"fieldname": "Mobile No","fieldtype": "Data","width": 100},
		{ "label": _("Email Id"),"fieldname": "Email Id","fieldtype": "Data","width": 120},
		{ "label": _("Lead Owner"),"fieldname": "Lead Owner","fieldtype": "Data","width": 120},
		{ "label": _("Source"),"fieldname": "Source","fieldtype": "Data","width": 120},
		{ "label": _("Territory"),"fieldname": "Territory","fieldtype": "Data","width": 120},
		{ "label": _("Owner"),"fieldname": "Owner","fieldtype": "Link","options":"User","width": 120}
				# _("Lead") + ":Link/Lead:100",  
				# _("Name") + "::120",
				# _("Company Name") + "::120",
				# _("Status") + "::80",
				# _("Address Line 1") + "::100",
				# _("Address Line 2") + "::100",
				# # _("Address") + ":Link/Address:130", #Address
				# _("State") + "::100",
				# _("City") + "::100", 
				# _("Pincode") + "::70",
				# _("Country") + ":100",  
				# _("Phone") + ":100", 
				# _("Mobile No") + "::100",
				# _("Email Id") + "::120",
				# _("Lead Owmer") + "::120",
				# _("Source") + "::120",
				# _("Territory") + "::120",
				# _("Owner") + ":Link/User:120"

	]
	return columns

def get_data(filters):
	where_clause = ''
	where_clause+=filters.name and " and `tabLead`.name = '%s' " %filters.name or ""
	where_clause+=filters.state and " and `tabAddress`.state = '%s' " %filters.state
	
	return frappe.db.sql("""
		SELECT

		    `tabLead`.name as "Lead",
		    `tabLead`.lead_name as "Name",
			`tabLead`.company_name as "Company Name",
			`tabLead`.status as "Status",

			-- concat_ws(', ', 
			-- 	trim(',' from `tabAddress`.address_line1), 
			-- 	trim(',' from `tabAddress`.address_line2)
			-- ) as 'Address',
			`tabAddress`.address_line1 as "Address Line 1",
			`tabAddress`.address_line2 as "Address Line 2",
			`tabAddress`.state as "State",
			`tabAddress`.city as "City",
			`tabAddress`.pincode as "Pincode",
			`tabAddress`.country as "Country",
			`tabLead`.phone as "Phone",
			`tabLead`.mobile_no as "Mobile No",
			`tabLead`.email_id as "Email Id",
			`tabLead`.lead_owner as "Lead Owner",
			`tabLead`.source as "Source",
			`tabLead`.territory as "Territory",
		    `tabLead`.owner as "Owner"
		FROM
			`tabLead`
		left join `tabDynamic Link` on (
			`tabDynamic Link`.link_name=`tabLead`.name
		)
		left join `tabAddress` on (
			`tabAddress`.name=`tabDynamic Link`.parent
		)
		WHERE
			`tabLead`.docstatus<2 
			%s
		ORDER BY
			`tabLead`.name asc """ %where_clause, as_dict=1)
			
	if filters.state == '':
		frappe.throw(_("Please Enter State"))