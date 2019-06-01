# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from erpnext.accounts.report.purchase_register.purchase_register import *

def execute(filters=None):
	return _execute(filters)

def _execute(filters=None, additional_table_columns=None, additional_query_columns=None):
	if not filters: filters = {}

	invoice_list = get_invoices(filters, additional_query_columns)
	columns, expense_accounts, tax_accounts = get_columns(invoice_list, additional_table_columns)

	if not invoice_list:
		msgprint(_("No record found"))
		return columns, invoice_list

	invoice_expense_map = get_invoice_expense_map(invoice_list)
	invoice_expense_map, invoice_tax_map = get_invoice_tax_map(invoice_list,
		invoice_expense_map, expense_accounts)
	invoice_po_pr_map = get_invoice_po_pr_map(invoice_list)
	suppliers = list(set([d.supplier for d in invoice_list]))
	supplier_details = get_supplier_details(suppliers)

	company_currency = frappe.db.get_value("Company", filters.company, "default_currency")

	data = []
	for inv in invoice_list:
		# invoice details
		purchase_order = list(set(invoice_po_pr_map.get(inv.name, {}).get("purchase_order", [])))
		purchase_receipt = list(set(invoice_po_pr_map.get(inv.name, {}).get("purchase_receipt", [])))
		project = list(set(invoice_po_pr_map.get(inv.name, {}).get("project", [])))

		row = [inv.name, inv.posting_date, inv.supplier, inv.supplier_name]

		if additional_query_columns:
			for col in additional_query_columns:
				row.append(inv.get(col))

		row += [
			supplier_details.get(inv.supplier), # supplier_type
			inv.tax_id, inv.credit_to, inv.mode_of_payment, ", ".join(project),
			inv.bill_no, inv.bill_date, inv.remarks,
			", ".join(purchase_order), ", ".join(purchase_receipt), company_currency
		]

		# map expense values
		base_net_total = 0
		for expense_acc in expense_accounts:
			expense_amount = flt(invoice_expense_map.get(inv.name, {}).get(expense_acc))
			base_net_total += expense_amount
			row.append(expense_amount)

		# net total
		row.append(base_net_total or inv.base_net_total)

		# tax account
		total_tax = 0
		for tax_acc in tax_accounts:
			if tax_acc not in expense_accounts:
				tax_amount = flt(invoice_tax_map.get(inv.name, {}).get(tax_acc))
				total_tax += tax_amount
				row.append(tax_amount)

		# total tax, grand total, outstanding amount & rounded total
		row += [total_tax, inv.base_grand_total, flt(inv.base_grand_total, 0), inv.outstanding_amount]
		data.append(row)

	return columns, data
