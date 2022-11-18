# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.utils import (
	is_reposting_item_valuation_in_progress,
	update_included_uom_in_report,
)


def execute(filters=None):
	is_reposting_item_valuation_in_progress()
	include_uom = filters.get("include_uom")
	columns = get_columns()
	items = get_items(filters)
	sl_entries = get_stock_ledger_entries(filters, items)
	item_details = get_item_details(items, sl_entries, include_uom)
	opening_row = get_opening_balance(filters, columns, sl_entries)
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))

	data = []
	conversion_factors = []
	if opening_row:
		data.append(opening_row)
		conversion_factors.append(0)

	actual_qty = stock_value = 0

	available_serial_nos = {}
	for sle in sl_entries:
		item_detail = item_details[sle.item_code]

		sle.update(item_detail)

		if filters.get("batch_no"):
			actual_qty += flt(sle.actual_qty, precision)
			stock_value += sle.stock_value_difference

			if sle.voucher_type == 'Stock Reconciliation' and not sle.actual_qty:
				actual_qty = sle.qty_after_transaction
				stock_value = sle.stock_value

			sle.update({
				"qty_after_transaction": actual_qty,
				"stock_value": stock_value
			})

		sle.update({
			"in_qty": max(sle.actual_qty, 0),
			"out_qty": min(sle.actual_qty, 0)
		})

		if sle.serial_no:
			update_available_serial_nos(available_serial_nos, sle)

		data.append(sle)

		if include_uom:
			conversion_factors.append(item_detail.conversion_factor)

	update_included_uom_in_report(columns, data, include_uom, conversion_factors)
	return columns, data

def update_available_serial_nos(available_serial_nos, sle):
	serial_nos = get_serial_nos(sle.serial_no)
	key = (sle.item_code, sle.warehouse)
	if key not in available_serial_nos:
		available_serial_nos.setdefault(key, [])

	existing_serial_no = available_serial_nos[key]
	for sn in serial_nos:
		if sle.actual_qty > 0:
			if sn in existing_serial_no:
				existing_serial_no.remove(sn)
			else:
				existing_serial_no.append(sn)
		else:
			if sn in existing_serial_no:
				existing_serial_no.remove(sn)
			else:
				existing_serial_no.append(sn)

	sle.balance_serial_no = '\n'.join(existing_serial_no)

def get_columns():
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Datetime", "width": 150},
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100},
		{"label": _("Item Name"), "fieldname": "item_name", "width": 100},
		{"label": _("Party Type"), "fieldname": "party_type", "fieldtype": "Data", "width": 80},
		{"label": _("Party"), "fieldname": "party", "fieldtype": "Dynamic Link", "options":"party_type","width": 140},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 110},
		{"label": _("Voucher #"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 100},
		{"label": _("Stock UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90},
		{"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Balance Qty"), "fieldname": "qty_after_transaction", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 100},
		{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 100},
		{"label": _("Description"), "fieldname": "description", "width": 200},
		{"label": _("Incoming Rate"), "fieldname": "incoming_rate", "fieldtype": "Currency", "width": 110, "options": "Company:company:default_currency", "convertible": "rate"},
		{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 110, "options": "Company:company:default_currency", "convertible": "rate"},
		{"label": _("Balance Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 110, "options": "Company:company:default_currency"},
		{"label": _("Batch"), "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 100},
		{"label": _("Serial No"), "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial No", "width": 100},
		{"label": _("Balance Serial No"), "fieldname": "balance_serial_no", "width": 100},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 100},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 110}
	]

	return columns


def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	if items:
		item_conditions_sql = 'and sle.item_code in ({})'\
			.format(', '.join(frappe.db.escape(i) for i in items))

	party_condition = ''
	if filters.get('party') and filters.get('party_type'):
		if filters.get('party_type') == 'Supplier':
			party_condition = """ and (pi.supplier = '{supplier}' or pr.supplier = '{supplier}' or se.party = '{supplier}') """.format(supplier=filters.get('party'))
		elif filters.get('party_type') == 'Customer':
			party_condition = """ and (si.customer = '{customer}' or dn.customer = '{customer}') """.format(customer=filters.get('party'))


	sl_entries = frappe.db.sql("""
		SELECT
			concat_ws(" ", sle.posting_date, sle.posting_time) AS date, sle.item_code, sle.warehouse, sle.actual_qty,
			sle.qty_after_transaction, sle.incoming_rate, sle.valuation_rate, sle.stock_value, sle.voucher_type,
			sle.voucher_no, sle.batch_no, sle.serial_no, sle.company, sle.project, sle.stock_value_difference,
			CASE WHEN sle.voucher_type in ('Purchase Receipt','Purchase Invoice') THEN 'Supplier'
			WHEN sle.voucher_type in ('Delivery Note','Sales Invoice') THEN 'Customer'
			WHEN sle.voucher_type in ('Stock Entry') THEN se.party_type
			END AS party_type,
			IFNULL(pr.supplier, IFNULL(pi.supplier,IFNULL(dn.customer,IFNULL(si.customer,se.party)))) as party
		FROM
			`tabStock Ledger Entry` sle
			LEFT JOIN `tabStock Entry` as se on se.name = sle.voucher_no
			LEFT JOIN `tabPurchase Receipt` as pr on pr.name = sle.voucher_no
			LEFT JOIN `tabPurchase Invoice` as pi on pi.name = sle.voucher_no
			LEFT JOIN `tabDelivery Note` as dn on dn.name = sle.voucher_no
			LEFT JOIN `tabSales Invoice` as si on si.name = sle.voucher_no
		WHERE
			sle.company = %(company)s
				AND sle.is_cancelled = 0 AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
				{sle_conditions}
				{item_conditions_sql}
				{party_condition}
		ORDER BY
			sle.posting_date asc, sle.posting_time asc, sle.creation asc
		""".format(sle_conditions=get_sle_conditions(filters), 
					item_conditions_sql=item_conditions_sql,
					party_condition = party_condition),
		filters, as_dict=1)

	return sl_entries


def get_items(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("item.name=%(item_code)s")
	else:
		if filters.get("brand"):
			conditions.append("item.brand=%(brand)s")
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	items = []
	if conditions:
		items = frappe.db.sql_list("""select name from `tabItem` item where {}"""
			.format(" and ".join(conditions)), filters)
	return items


def get_item_details(items, sl_entries, include_uom):
	item_details = {}
	if not items:
		items = list(set(d.item_code for d in sl_entries))

	if not items:
		return item_details

	cf_field = cf_join = ""
	if include_uom:
		cf_field = ", ucd.conversion_factor"
		cf_join = "left join `tabUOM Conversion Detail` ucd on ucd.parent=item.name and ucd.uom=%s" \
			% frappe.db.escape(include_uom)

	res = frappe.db.sql("""
		select
			item.name, item.item_name, item.description, item.item_group, item.brand, item.stock_uom {cf_field}
		from
			`tabItem` item
			{cf_join}
		where
			item.name in ({item_codes})
	""".format(cf_field=cf_field, cf_join=cf_join, item_codes=','.join(['%s'] *len(items))), items, as_dict=1)

	for item in res:
		item_details.setdefault(item.name, item)

	return item_details


def get_sle_conditions(filters):
	conditions = []
	if filters.get("warehouse"):
		warehouse_condition = get_warehouse_condition(filters.get("warehouse"))
		if warehouse_condition:
			conditions.append(warehouse_condition)
	if filters.get("voucher_no"):
		conditions.append("sle.voucher_no=%(voucher_no)s")
	if filters.get("batch_no"):
		conditions.append("sle.batch_no=%(batch_no)s")
	if filters.get("project"):
		conditions.append("sle.project=%(project)s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""


def get_opening_balance(filters, columns, sl_entries):
	if not (filters.item_code and filters.warehouse and filters.from_date):
		return

	from erpnext.stock.stock_ledger import get_previous_sle
	last_entry = get_previous_sle({
		"item_code": filters.item_code,
		"warehouse": filters.warehouse,
		"posting_date": filters.from_date,
		"posting_time": "00:00:00"
	})

	# check if any SLEs are actually Opening Stock Reconciliation
	for sle in sl_entries:
		if (sle.get("voucher_type") == "Stock Reconciliation"
			and sle.get("date").split()[0] == filters.from_date
			and frappe.db.get_value("Stock Reconciliation", sle.voucher_no, "purpose") == "Opening Stock"
		):
			last_entry = sle
			sl_entries.remove(sle)

	row = {
		"item_code": _("'Opening'"),
		"qty_after_transaction": last_entry.get("qty_after_transaction", 0),
		"valuation_rate": last_entry.get("valuation_rate", 0),
		"stock_value": last_entry.get("stock_value", 0)
	}

	return row


def get_warehouse_condition(warehouse):
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
	if warehouse_details:
		return " exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s and sle.warehouse = wh.name)"%(warehouse_details.lft,
			warehouse_details.rgt)

	return ''


def get_item_group_condition(item_group):
	item_group_details = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=1)
	if item_group_details:
		return "item.item_group in (select ig.name from `tabItem Group` ig \
			where ig.lft >= %s and ig.rgt <= %s and item.item_group = ig.name)"%(item_group_details.lft,
			item_group_details.rgt)

	return ''