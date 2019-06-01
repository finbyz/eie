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
	columns = [_("Lead") + ":Link/Lead:100",  
				_("Name") + "::120",
				_("Company Name") + "::120",
				_("Status") + "::80",
				_("Address Line 1") + "::100",
				_("Address Line 2") + "::100",
				# _("Address") + ":Link/Address:130", #Address
				_("State") + "::100",
				_("City") + "::100", 
				_("Pincode") + "::70",
				_("Country") + ":100",  
				_("Phone") + ":100", 
				_("Mobile No") + "::100",
				_("Email Id") + "::120",
				_("Lead Owmer") + "::120",
				_("Source") + "::120",
				_("Territory") + "::120",
				_("Owner") + ":Link/User:120"

	]
	return columns

def get_data(filters):
	where_clause = ''
	where_clause+=filters.name and " and Lead = '%s' " %filters.name or ""
	where_clause+=filters.state and " and State = '%s' " %filters.state
	
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