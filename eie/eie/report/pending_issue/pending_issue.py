# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_data(filters):
	where_clause = ''
	where_clause += filters.state and " and state = '%s'" %filters.state or ""

	return frappe.db.sql("""
		SELECT 
			name as "ID", subject as "Subject", issue_type as "Issue Type", status as "Status", raised_by as "Raised By (Email)", customer as "Customer", customer_address as "Customer Address", contact_person as "Contact Person", contact_email as "Contact Email", state as "State", item_code as "Item Code", item_name as "Item Name", warranty_amc_status as"Warranty / AMC Status", warranty_expiry_date as "Warranty Expiry Date", amc_expiry_date as "AMC Expiry Date", customer_name as "Customer Name", company as"Company", opening_date as "Opening Date", resolution_date as "Resolution Date", engineer as "Engineer", visit_charge as "Visit Charge", engineer_name as "Engineer Name", engineer_contact as "Engineer Contact", engineer_email as "Engineer Email"
		FROM 
			`tabIssue` 
		WHERE
			status != "Closed" 
			%s """ %where_clause, as_dict=1)

def get_columns():
	columns= [
		_("ID") + ":Link/Issue:80",
		_("Subject") + ":Data:100",
		_("Issue Type") + ":Link/Item:120",
		_("Status") + ":Data:80",
		_("Raised By") + ":Data:120",
		_("Customer") + ":Link/Customer:120",
		_("Customer Address") + ":Link/Address:120",
		_("Contact Person") + ":Link/Contact:120",
		_("Contact Email") + ":Data:100",
		_("Contact Mobile") + ":Data:120",
		_("State") + ":Data:120",
		_("Item Code") + ":Link/Item:120",
		_("Item Name") + ":Data:120",
		_("Warranty / AMC Status") + ":Data:120",
		_("Warranty Expiry Date") + ":Date:120",
		_("AMC Expiry Date") + ":Date:120",
		_("Customer Name") + ":Data:120",
		_("Company") + ":Data:120",
		_("Opening Date") + ":Date:120",
		_("Resolution Date") + ":Datetime:120",
		_("Engineer") + ":Link/Employee:120",
		_("Engineer Name") + ":Data:120",
		_("Engineer Contact") + ":Data:120",
		_("Engineer Email") + ":Data:120",
		_("Visit Charge") + ":Float:120",
	]
	return columns
