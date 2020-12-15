# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate, getdate

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()
	data = get_entries(filters)

	return columns, data

def get_columns():
	# Finbyz Changes
	return [
		{ "label": _("Payment Document"),"fieldname": "Payment Document","fieldtype": "Data","width": 130},
		{ "label": _("Payment Entry"),"fieldname": "Payment Entry","fieldtype": "Dynamic Link","options":"Payment Document","width": 110},
		{ "label": _("Posting Date"),"fieldname": "Posting Date","fieldtype": "Date","width": 100},
		{ "label": _("Cheque/Reference No"),"fieldname": "Cheque/Reference No","fieldtype": "Data","width": 120},
		{ "label": _("Clearance Date"),"fieldname": "Clearance Date","fieldtype": "Date","width": 100},
		{ "label": _("Against Account"),"fieldname": "Against Account","fieldtype": "Link","options":"Account","width": 170},
		{ "label": _("Amount"),"fieldname": "Amount","fieldtype": "Currency","width": 120},
		# _("Payment Document") + "::130",
		# _("Payment Entry") + ":Dynamic Link/"+_("Payment Document")+":110",
		# _("Posting Date") + ":Date:100",
		# _("Cheque/Reference No") + "::120",
		# _("Clearance Date") + ":Date:100",
		# _("Against Account") + ":Link/Account:170",
		# _("Amount") + ":Currency:120"
	]

def get_conditions(filters):
	conditions = ""

	if filters.get("from_date"): conditions += " and posting_date>=%(from_date)s"
	if filters.get("to_date"): conditions += " and posting_date<=%(to_date)s"

	return conditions

def get_entries(filters):
	conditions = get_conditions(filters)
	journal_entries =  frappe.db.sql("""SELECT
			"Journal Entry", jv.name, jv.posting_date, jv.cheque_no,
			jv.clearance_date, jvd.against_account, jvd.debit - jvd.credit
		FROM 
			`tabJournal Entry Account` jvd, `tabJournal Entry` jv
		WHERE 
			jvd.parent = jv.name and jv.docstatus=1 and jvd.account = %(account)s {0}
			order by posting_date DESC, jv.name DESC""".format(conditions), filters, as_list=1)

	payment_entries =  frappe.db.sql("""SELECT
			"Payment Entry", name, posting_date, reference_no, clearance_date, party, 
			if(paid_from=%(account)s, paid_amount * -1, received_amount)
		FROM 
			`tabPayment Entry`
		WHERE 
			docstatus=1 and (paid_from = %(account)s or paid_to = %(account)s) {0}
			order by posting_date DESC, name DESC""".format(conditions), filters, as_list=1)

	return sorted(journal_entries + payment_entries, key=lambda k: k[2] or getdate(nowdate()))
