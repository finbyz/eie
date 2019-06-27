# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		_("Full Name") + ":Data:150",
		_("Email ID") + ":Data:150",
		_("Phone No") + ":Data:120",
		_("Mobile No") + ":Data:120",
		_("Customer Name") + ":Data:150",
		_("Industry") + ":Link/Industry Type:120",
		_("Referece DocType") + ":Data:120",
		_("Referece Name") + ":Dynamic Link/" + _("Referece DocType")+":120",
	]

def get_data(filters):
	details = get_contact_details(filters)
	data = []

	for detail in details:
		row = {
			"Full Name": cstr(detail.first_name) + " " + cstr(detail.last_name),
			"Email ID": detail.email_id,
			"Phone No": detail.phone,
			"Mobile No": detail.mobile_no,
			"Customer Name": detail.customer_name,
			"Industry": detail.industry,
			"Referece DocType": detail.link_doctype,
			"Referece Name": detail.link_name,
		}

		data.append(row)

	return data

def get_filtered_conditions(filters):
	conditions = [
		["Dynamic Link", "link_doctype", "in", ["Customer", "Lead"]],
	]

	if filters.get('has_email'):
		conditions.append(["Contact", "email_id", "!=", ""])

	if filters.get('has_phone_no'):
		conditions.append(["Contact", "phone", "!=", ""])

	if filters.get('has_mobile_no'):
		conditions.append(["Contact", "mobile_no", "!=", ""])

	return conditions

def get_contact_details(filters):

	conditions = get_filtered_conditions(filters)
	fields = ["`tabDynamic Link`.link_doctype", "`tabDynamic Link`.link_name", "first_name", "last_name", "email_id", "phone", "mobile_no", "name"]

	data = frappe.get_list("Contact", filters=conditions, fields=fields)
	temp_records = frappe._dict()

	customer_field_map = {
		"Customer": "customer_name",
		"Lead": "company_name"
	}

	for row in data:
		customer_name, industry = frappe.db.get_value(row.link_doctype, row.link_name, [
				customer_field_map.get(row.link_doctype), 'industry'])

		if filters.get('industry') and industry != filters.get('industry'):
			continue

		if row.name not in temp_records:
			temp_records.setdefault(row.name, row)

		elif temp_records[row.name].link_doctype == "Lead":
			temp_records[row.name] = row
		
		temp_records[row.name].customer_name = customer_name
		temp_records[row.name].industry = industry

	records = [values for key, values in temp_records.items()]
	return records
