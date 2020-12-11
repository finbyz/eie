# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import json
import frappe, erpnext
import re
import time
from frappe import _, db
from erpnext.utilities.product import get_price
from frappe.contacts.doctype.address.address import get_address_display, get_default_address, get_company_address
from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact
from frappe.desk.reportview import get_match_cond, get_filters_cond
from frappe.utils import nowdate, get_url_to_form, flt, cstr, getdate, get_fullname, now_datetime, parse_val, add_years, add_days
from frappe.model.mapper import get_mapped_doc
from frappe.utils.background_jobs import enqueue
from email.utils import formataddr
from frappe.core.doctype.communication.email import make
import datetime 
from six import itervalues, string_types
from erpnext.manufacturing.doctype.bom.bom import add_additional_cost

@frappe.whitelist()
def validate_serial_nos(self, method):

	for row in self.items:
		if hasattr(row,'s_warehouse'):
			if row.s_warehouse:
				continue

		has_serial_no = db.get_value("Item", row.item_code, 'has_serial_no')
		if has_serial_no:
			if not row.serial_no:
				frappe.throw(_("Serial Number is required for Item <b>{0}</b> in row {1}").format(row.item_code, row.idx))
				validated = False
			else:
				serial_nos = get_serial_nos(row.serial_no)
				if len(serial_nos) != row.qty:
					frappe.throw(_("{0} serial numbers are missing for Item <b>{1}</b> in row {2}").format(row.qty - len(serial_nos), row.item_code, row.idx))
					validated = False
				elif ((self.doctype == "Stock Entry" and row.get('t_warehouse', ''))
						or self.doctype == "Purchase Receipt"):
					new_serial_no = serial_nos[:]
					abbr = db.get_value("Company", self.company, 'abbr')
					abbr_len = (len(abbr) + 1) * -1

					flag = True
					while flag:
						flag = False
						for i, sr_no in enumerate(serial_nos):
							if db.exists("Serial No", {'name': sr_no, 'purchase_document_type': ["!=", '']}):
								flag = True
								new_serial_no[i] = sr_no[:abbr_len] + '1' + sr_no[abbr_len:]		
						serial_nos = new_serial_no[:]
					row.serial_no = '\n'.join(new_serial_no)
		else:
			row.serial_no = ''

@frappe.whitelist()
def pe_validate(self,method):
	for row in self.references:
		if db.get_value(row.reference_doctype, row.reference_name, 'company') != self.company:
			frappe.throw("Your Reference Row %d is of different company!" % row.idx)

@frappe.whitelist()
def pi_before_save(self, method):
	update_serial_no(self, method)
	tax_breakup_data(self)

def bom_validate(self,method):
	calculate_total(self)
	
def bom_on_update_after_submit(self,method):
	calculate_total(self)

@frappe.whitelist()
def IP_before_save(self,method):
	fetch_item_grouo(self)

@frappe.whitelist()
def SE_before_save(self,method):
	update_serial_no(self, method)

def customer_before_save(self,method):
	update_industry(self)


def update_industry(self):
	if self.lead_name:
		lead = frappe.get_doc("Lead",self.lead_name)
		lead.industry = self.industry
		lead.save()

def mr_before_save(self, method):
	set_default_supplier(self)

def set_default_supplier(self):
	for row in self.items:
		row.default_supplier = cstr(frappe.db.get_value("Item Default", 
			filters={
				'parent': row.item_code,
				'company': self.company,
			}, fieldname=('default_supplier')))

@frappe.whitelist()
def update_serial_no(self, method):

	company_abbr = db.get_value("Company", self.company, 'abbr')
	company_abbr_len = (len(company_abbr) + 1) * -1

	other_abbr = frappe.get_list("Company", filters=[['abbr', '!=', company_abbr]], fields='abbr')

	for row in self.items:
		new_serial_no = []
		if not row.serial_no:
			continue
		try:
			if not row.t_warehouse:
				continue
		except:
			pass
		serial_nos = get_serial_nos(row.serial_no)
		for sr_no in serial_nos:
			for abbr in other_abbr:
				other_abbr_len = (len(abbr['abbr']) + 1) * -1
				if sr_no[other_abbr_len:] == "-" + abbr['abbr']:
					sr_no = sr_no[:other_abbr_len]
			if sr_no[company_abbr_len:] != "-" + company_abbr:
				new_serial_no.append(sr_no + '-' + company_abbr)
			else:
				new_serial_no.append(sr_no)
		row.serial_no = '\n'.join(new_serial_no)

def get_serial_nos(serial_no):
	return [s.strip() for s in cstr(serial_no).strip().upper().replace(',', '\n').split('\n')
		if s.strip()]

@frappe.whitelist()
def update_actual_serial_no(self, method):
	abbr = db.get_value("Company", self.company, 'abbr')
	abbr_len = (len(abbr) + 1) * -1

	if not self.actual_serial_no and self.serial_no[abbr_len:] == "-" + abbr:
		self.db_set('actual_serial_no', self.serial_no[:abbr_len])
		db.commit()

@frappe.whitelist()
def si_on_submit(self, method):
	if db.exists("Company", self.customer):
		create_purchase_invoice(self)

@frappe.whitelist()
def si_on_cancel(self, method):
	if db.exists("Purchase Invoice", self.purchase_invoice):
		cancel_purchase_invoice(self)

def create_purchase_invoice(self):
	pi = frappe.new_doc("Purchase Invoice")
	
	old_abbr = db.get_value("Company", self.company, 'abbr')
	new_abbr = db.get_value("Company", self.customer, 'abbr')
	
	pi.posting_date = self.posting_date
	pi.posting_time = self.posting_time
	pi.set_posting_time = self.set_posting_time
	pi.naming_series = db.get_value("Company", self.customer, 'purchase_invoice')
	pi.company = self.customer
	pi.supplier = self.company
	pi.due_date = self.due_date
	pi.bill_no = self.name
	pi.bill_date = self.posting_date
	pi.currency = self.currency
	pi.update_stock = self.update_stock

	for item in self.items:
		pi.append('items', {
			'item_code': item.item_code,
			'item_name': item.item_name,
			'qty': item.qty,
			'rate': item.rate,
			'description': item.description,
			'uom': item.uom,
			'price_list_rate': item.price_list_rate,
			'rate': item.rate,
			'original_rate': item.original_rate,
			'discount_per': item.discount_per,
			'purchase_order': frappe.db.get_value("Purchase Order Item", item.purchase_order_item, 'parent'),
			'po_detail': item.purchase_order_item,
			'warehouse': 'Stores - %s' % new_abbr,
		})

	pi.taxes_and_charges = self.taxes_and_charges
	pi.shipping_rule = self.shipping_rule
	pi.shipping_address = self.shipping_address_name
	pi.shipping_address_display = self.shipping_address
	pi.tc_name = 'Purchase Terms'

	for tax in self.taxes:
		account_head = tax.account_head.replace(old_abbr, new_abbr)
		if not db.exists("Account", account_head):
			frappe.msgprint(_("The Account Head <b>{0}</b> does not exists. Please create Account Head for company <b>{1}</b> and create Purchase Invoice manually.".format(_(account_head), _(self.customer))), title="Purchase Invoice could not be created", indicator='red')
			return

		pi.append('taxes',{
			'charge_type': tax.charge_type,
			'row_id': tax.row_id,
			'account_head': account_head,
			'description': tax.description.replace(old_abbr, ''),
			'rate': tax.rate,
			'tax_amount': tax.tax_amount,
			'total': tax.total
		})

	pi.save()
	self.db_set('purchase_invoice', pi.name)
	pi.submit()
	db.commit()

	url = get_url_to_form("Purchase Invoice", pi.name)
	frappe.msgprint(_("Purchase Invoice <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=pi.name)), title="Purchase Invoice Created", indicator="green")

def cancel_purchase_invoice(self):
	pi = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
	pi.cancel()
	self.db_set('purchase_invoice','')
	db.commit()

	url = get_url_to_form("Purchase Invoice", pi.name)
	frappe.msgprint(_("Purchase Invoice <b><a href='{url}'>{name}</a></b> has been cancelled!".format(url=url, name=pi.name)), title="Purchase Invoice Cancelled", indicator="green")

@frappe.whitelist()
def po_on_submit(self, method):
	if db.exists("Company", self.supplier):
		create_sales_order(self)

@frappe.whitelist()
def po_on_cancel(self, method):
	if db.exists("Sales Order", self.sales_order):
		cancel_sales_order(self)

def create_sales_order(self):
	so = frappe.new_doc("Sales Order")
	so.naming_series = db.get_value("Company", self.supplier, 'sales_order')
	so.company = self.supplier
	so.customer = self.company
	so.delivery_date = self.schedule_date
	so.transaction_date = self.transaction_date
	so.po_no = self.name
	so.po_date = self.transaction_date
	so.currency = self.currency
	so.actual_customer = self.actual_customer
	so.shipping_address_name = self.shipping_address
	so.shipping_address = self.shipping_address_display
	so.customer_address = get_company_address(self.company).company_address
	so.address_display = get_company_address(self.company).company_address_display

	old_abbr = db.get_value("Company", self.company, 'abbr')
	new_abbr = db.get_value("Company", self.supplier, 'abbr')

	for item in self.items:
		so.append('items',{
			'item_code': item.item_code,
			'item_name': item.item_name,
			'delivery_date': item.schedule_date,
			'gst_hsn_code': item.gst_hsn_code,
			'qty': item.qty,
			'uom': item.uom,
			'price_list_rate': item.price_list_rate,
			'rate': item.rate,
			'original_rate': item.original_rate,
			'discount_per': item.discount_per,
			'warehouse': 'Stores - %s' % new_abbr,
			'purchase_order_item': item.name,
			'actual_customer': item.actual_customer
		})

	for tax in self.taxes:
		account_head = tax.account_head.replace(old_abbr, new_abbr)
		if not db.exists("Account", account_head):
			frappe.throw(_("The Account Head <b>{0}</b> does not exists. Please create Account Head for company <b>{1}</b> and create Purchase Order manually.".format(_(account_head), _(self.customer))), title="Purchase Order could not be created", indicator='red')
			return

		so.append('taxes',{
			'charge_type': tax.charge_type,
			'account_head': account_head,
			'description': tax.description.replace(old_abbr, ''),
			'rate': tax.rate,
		})

	so.payment_terms_template = self.payment_terms_template

	for payment in self.payment_schedule:
		so.append('payment_schedule',{
			'payment_term': payment.payment_term,
			'description': payment.description,
			'due_date': payment.due_date,
			'invoice_portion': payment.invoice_portion,
			'payment_amount': payment.payment_amount,
		})

	so.tc_name = 'Sales Order Conditions'
	so.save()
	self.db_set('sales_order', so.name)
	so.submit()
	db.commit()

	url = get_url_to_form("Sales Order", so.name)
	frappe.msgprint(_("Sales Order <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=so.name)), title="Sales Order Created", indicator="green")
		
def cancel_sales_order(self):
	so = frappe.get_doc("Sales Order", self.sales_order)
	so.cancel()
	self.db_set('sales_order', '')
	db.commit()

	url = get_url_to_form("Sales Order", so.name)
	frappe.msgprint(_("Sales Order <b><a href='{url}'>{name}</a></b> has been cancelled!".format(url=url, name=so.name)), title="Sales Order Cancelled", indicator="green")

@frappe.whitelist()
def dn_before_save(self, method):
	calculate_combine(self)

@frappe.whitelist()
def dn_on_submit(self, method):
	if db.exists("Company", self.customer):
		if not db.exists("Purchase Order", self.po_no):
			url = get_url_to_form("Purchase Order", self.po_no)
			frappe.throw("The Purchase Order <b><a href='{url}'>{name}</a></b> might have been cancelled or does not exist!".format(url=url, name=self.po_no))
		else:
			create_purchase_receipt(self)

@frappe.whitelist()
def dn_on_cancel(self, method):
	if db.exists("Purchase Receipt", self.purchase_receipt):
		cancel_purchase_receipt(self)

def create_purchase_receipt(self):
	pr = frappe.new_doc("Purchase Receipt")
	pr.supplier_delivery_note = self.name
	pr.naming_series = db.get_value("Company", self.customer, 'purchase_receipt')
	pr.posting_date = self.posting_date
	pr.posting_time = self.posting_time
	pr.set_posting_time = self.set_posting_time
	pr.company = self.customer
	pr.supplier = self.company
	pr.currency = self.currency

	old_abbr = db.get_value("Company", self.company, 'abbr')
	new_abbr = db.get_value("Company", self.customer, 'abbr')

	cost_center = db.get_value("Company", self.customer, 'cost_center')

	for item in self.items:
		pr.append('items',{
			'item_code': item.item_code,
			'item_name': item.item_name,
			'qty': item.qty,
			'uom': item.uom,
			'price_list_rate': item.price_list_rate,
			'rate': item.rate,
			'original_rate': item.original_rate,
			'discount_per': item.discount_per,
			'amount': item.amount,
			'stock_qty': item.stock_qty,
			'warehouse': 'Stores - %s' % new_abbr,
			'serial_no': item.serial_no,
			'cost_center': cost_center,
			'purchase_order': self.po_no,
			'purchase_order_item': item.purchase_order_item
		})

	if db.exists({"doctype": "Sales Taxes and Charges Template", 
			"name": self.taxes_and_charges, "company": self.customer}):
		pr.taxes_and_charges = self.taxes_and_charges

	pr.shipping_rule = self.shipping_rule

	for tax in self.taxes:
		account_head = tax.account_head.replace(old_abbr, new_abbr)
		if not db.exists("Account", account_head):
			frappe.msgprint(_("The Account Head <b>{0}</b> does not exists. Please create Account Head for company <b>{1}</b> and create Purchase Receipt manually.".format(_(account_head), _(self.customer))), title="Purchase Receipt could not be created", indicator='red')
			return

		pr.append('taxes',{
			'charge_type': tax.charge_type,
			'row_id': tax.row_id,
			'account_head': account_head,
			'description': tax.description.replace(old_abbr, ''),
			'rate': tax.rate,
			'tax_amount': tax.tax_amount,
			'total': tax.total,
			'cost_center': cost_center,
		})

	pr.tc_name = 'Purchase Terms'
	try:
		pr.save()
	except Exception as e:
		frappe.throw(_(e))
	else:
		self.db_set('purchase_receipt', pr.name)
		db.commit()

	url = get_url_to_form("Purchase Receipt", pr.name)
	frappe.msgprint(_("Purchase Receipt <b><a href='{url}'>{name}</a></b> has been created successfully! Please submit the Purchase Recipient.".format(url=url, name=pr.name)), title="Purchase Receipt Created", indicator="green")

def cancel_purchase_receipt(self):
	pr = frappe.get_doc("Purchase Receipt", self.purchase_receipt)
	self.db_set('purchase_receipt', '')
	pr.cancel()
	db.commit()

	url = get_url_to_form("Purchase Receipt", pr.name)
	frappe.msgprint(_("Purchase Receipt <b><a href='{url}'>{name}</a></b> has been cancelled!".format(url=url, name=pr.name)), title="Purchase Receipt Cancelled", indicator="green")


@frappe.whitelist()
def get_spare_price(item_code, price_list, customer_group, company):
	
	price = get_price(item_code, price_list, customer_group, company)
	return price

@frappe.whitelist()
def get_party_details(party=None, party_type="Customer", ignore_permissions=False):

	if not party:
		return {}

	if not db.exists(party_type, party):
		frappe.throw(_("{0}: {1} does not exists").format(party_type, party))

	return _get_party_details(party, party_type, ignore_permissions)

def _get_party_details(party=None, party_type="Customer", ignore_permissions=False):

	out = frappe._dict({
		party_type.lower(): party
	})

	party = out[party_type.lower()]

	if not ignore_permissions and not frappe.has_permission(party_type, "read", party):
		frappe.throw(_("Not permitted for {0}").format(party), frappe.PermissionError)

	party = frappe.get_doc(party_type, party)
	
	set_address_details(out, party, party_type)
	set_contact_details(out, party, party_type)
	set_other_values(out, party, party_type)

	if party_type == 'Lead':
		out.organisation = party.company_name
	elif party_type == 'Customer':
		out.organisation = party.customer_name

	return out

def set_address_details(out, party, party_type):
	billing_address_field = "customer_address" if party_type == "Lead" \
		else party_type.lower() + "_address"
	out[billing_address_field] = get_default_address(party_type, party.name)
	
	out.address_display = get_address_display(out[billing_address_field])

def set_contact_details(out, party, party_type):
	out.contact_person = get_default_contact(party_type, party.name)

	if not out.contact_person:
		out.update({
			"contact_person": None,
			"contact_display": None,
			"contact_email": None,
			"contact_mobile": None,
			"contact_phone": None,
			"contact_designation": None,
			"contact_department": None
		})
	else:
		out.update(get_contact_details(out.contact_person))

def set_other_values(out, party, party_type):
	# copy
	if party_type=="Customer":
		to_copy = ["customer_name", "customer_group", "territory", "language"]
	else:
		to_copy = ["supplier_name", "supplier_type", "language"]
	for f in to_copy:
		out[f] = party.get(f)

def filter_installation_note(doctype, txt, searchfield, start, page_len, filters, as_dict=False):

	return db.sql("""
		SELECT 
			`tabInstallation Note`.name
		FROM
			`tabInstallation Note` join `tabInstallation Note Item` on (`tabInstallation Note`.name = `tabInstallation Note Item`.parent)
		where
			`tabInstallation Note`.docstatus < 2
			and (`tabInstallation Note`.`{key}` LIKE %(txt)s)
			{fcond}
		order by
			if(locate(%(_txt)s, `tabInstallation Note`.name), locate(%(_txt)s, `tabInstallation Note`.name), 99999),
			if(locate(%(_txt)s, `tabInstallation Note Item`.item_code), locate(%(_txt)s, `tabInstallation Note Item`.item_code), 99999) 
		limit %(start)s, %(page_len)s """.format(
				key=searchfield,
				fcond= get_filters_cond("Installation Note Item", filters, []).replace('%', '%%')),
				{	
					"txt": "%s%%" % txt,
					"_txt": txt.replace("%", ""),
					"start": start,
					"page_len": page_len
				} , as_dict=as_dict)

# def new_item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
# 	conditions = []

# 	return db.sql("""
# 		select
# 			tabItem.name, tabItem.item_other_names, tabItem.item_group
# 		from
# 			tabItem
# 		where 
# 			tabItem.docstatus < 2
# 			and tabItem.has_variants=0
# 			and tabItem.disabled=0
# 			and (tabItem.end_of_life > %(today)s or ifnull(tabItem.end_of_life, '0000-00-00')='0000-00-00')
# 			and (tabItem.`{key}` LIKE %(txt)s
# 				or tabItem.item_name LIKE %(txt)s
# 				or tabItem.item_group LIKE %(txt)s
# 				or tabItem.item_other_names LIKE %(txt)s
# 				or tabItem.barcode LIKE %(txt)s)
# 			{fcond} {mcond}
		
# 		order by
# 			default_selection desc,
# 			if(locate(%(_txt)s, tabItem.name), locate(%(_txt)s, tabItem.name), 99999),
# 			if(locate(%(_txt)s, item_name), locate(%(_txt)s, item_name), 99999)
			
# 		limit %(start)s, %(page_len)s """.format(
# 			key=searchfield,
# 			fcond=get_filters_cond(doctype, filters, conditions).replace('%', '%%'),
# 			mcond=get_match_cond(doctype).replace('%', '%%')),
# 			{
# 				"today": nowdate(),
# 				"txt": "%s%%" % txt,
# 				"_txt": txt.replace("%", ""),
# 				"start": start,
# 				"page_len": page_len
# 			}, as_dict=as_dict)

@frappe.whitelist()
def new_item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	conditions = []
	return db.sql("""
		select
			tabItem.name, tabItem.item_other_names, tabItem.item_group, if((bin.actual_qty>0),CONCAT_WS(':',bin.company,bin.actual_qty),0)
		from
			tabItem

		LEFT JOIN (
		  SELECT b.item_code,round(sum(b.actual_qty),2) as actual_qty, w.company
		  FROM `tabBin` as b
		  LEFT JOIN `tabWarehouse` as w ON w.name = warehouse 
		  GROUP BY b.item_code,w.company
		) as bin ON (tabItem.name = bin.item_code and tabItem.is_stock_item = 1) 			
			
		where 
			tabItem.docstatus < 2
			and tabItem.has_variants=0
			and tabItem.disabled=0
			and (tabItem.`{key}` LIKE %(txt)s
				or tabItem.item_name LIKE %(txt)s
				or tabItem.item_group LIKE %(txt)s
				or tabItem.item_other_names LIKE %(txt)s
				or tabItem.barcode LIKE %(txt)s)
			{fcond} {mcond}
		order by
			bin.actual_qty desc,
			default_selection desc,
			if(locate(%(_txt)s, tabItem.name), locate(%(_txt)s, tabItem.name), 99999),
			if(locate(%(_txt)s, item_name), locate(%(_txt)s, item_name), 99999)
			
		limit %(start)s, %(page_len)s """.format(
			key=searchfield,
			fcond=get_filters_cond(doctype, filters, conditions).replace('%', '%%'),
			mcond=get_match_cond(doctype).replace('%', '%%')),
			{
				"txt": "%s%%" % txt,
				"_txt": txt.replace("%", ""),
				"start": start,
				"page_len": page_len
			}, as_dict=as_dict)

def filter_po_item(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	data = frappe.get_list("Product Bundle", fields='new_item_code')
	item_list = [d.new_item_code for d in data]
	if not filters:
		filters = []
	filters.append(['Item', 'item_code', 'NOT IN', item_list])
	return new_item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False)
	
@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	def postprocess(source, doc):
		doc.material_request_type = "Purchase"

		if hasattr(doc,'items'):
			for row in doc.items:
				tot_avail_qty = db.sql("select projected_qty from `tabBin` \
					where item_code = %s and warehouse = %s", (row.item_code, row.warehouse))
				projected_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0
				
				row.qty = abs(projected_qty)

	def update_item(source, target, source_parent):
		target.project = source_parent.project

	def check_items(doc):
		if db.exists('Product Bundle', doc.item_code):
			return False
		
		tot_avail_qty = db.sql("select projected_qty from `tabBin` \
			where item_code = %s and warehouse = %s", (doc.item_code, doc.warehouse))
		projected_qty = tot_avail_qty and flt(tot_avail_qty[0][0]) or 0

		if projected_qty < 0:
			return True
			
		return False

	doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Material Request",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Material Request Item",
			"field_map": {
				"name": "sales_order_item",
				"parent": "sales_order",
				"stock_uom": "uom"
			},
			"postprocess": update_item,
			"condition": check_items
		},
		"Packed Item": {
			"doctype": "Material Request Item",
			"field_map": {
				"parent": "sales_order",
				"stock_uom": "uom"
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.projected_qty < 0
		}
	}, target_doc, postprocess)

	return doc

@frappe.whitelist()
def si_before_save(self, method):
	tax_breakup_data(self)
	calculate_combine(self)


@frappe.whitelist()
def so_before_save(self, method):
	tax_breakup_data(self)
	calculate_combine(self)

def so_before_update_after_submit(self, method):
	calculate_combine(self)

@frappe.whitelist()
def qt_before_save(self, method):
	calculate_combine(self)


def calculate_combine(self):
	main_item_object_dict = {}
	main_item_dict = {}

	count = 0
	for row in self.items:
		if row.discount_per:
			disc = flt(row.original_rate, row.precision('original_rate')) * flt(row.discount_per, row.precision('discount_per')) / 100.0
			rate = flt(row.original_rate, row.precision('original_rate')) - disc
			row.rate = flt(rate, row.precision('rate'))

		if not row.price_list_rate:
			row.price_list_rate = flt(row.rate, row.precision('price_list_rate'))

		price_list_amount = flt(row.price_list_rate) * row.qty
		combined_original_amount = flt(row.original_rate) * row.qty
		com_rate = flt(row.net_rate) * row.qty
		com_amount = flt(row.net_amount)

		if row.main_item:
			main_item_dict.setdefault(row.main_item, {'price_list_amount': 0.0, 'combined_original_amount': 0.0, 'com_rate': 0.0, 'com_amount': 0.0})
			
			main_item_dict[row.main_item]['price_list_amount'] += price_list_amount
			main_item_dict[row.main_item]['combined_original_amount'] += combined_original_amount
			main_item_dict[row.main_item]['com_rate'] += com_rate
			main_item_dict[row.main_item]['com_amount'] += com_amount

		else:
			main_item_object_dict.setdefault(row.item_code, row)

			if row.get('index_no'):
				row.row_index = row.index_no
			else:
				count += 1
				row.row_index = count

		row.combine_price_list_rate = price_list_amount / row.qty
		row.combine_rate = com_rate / row.qty
		row.combine_original_rate = combined_original_amount / row.qty
		row.combined_amount = com_amount
		row.combine_percentage = (flt(row.combine_price_list_rate) - flt(row.combine_rate)) * 100 / row.combine_price_list_rate if row.combine_price_list_rate else 0.0
		row.combine_discount = (flt(row.combine_original_rate- row.combine_rate)) * 100 / row.combine_original_rate if row.combine_original_rate else 0.0

	for item_code, values in main_item_dict.items():
		main_item = main_item_object_dict.get(item_code)
		if main_item:
			main_item.combine_price_list_rate += main_item_dict[item_code]['price_list_amount'] / main_item.qty
			main_item.combine_rate += main_item_dict[item_code]['com_rate'] / main_item.qty
			main_item.combine_original_rate += main_item_dict[item_code]['combined_original_amount'] / main_item.qty
			main_item.combined_amount += main_item_dict[item_code]['com_amount']
			main_item.combine_percentage = (flt(main_item.combine_price_list_rate) - flt(main_item.combine_rate)) * 100 / main_item.combine_price_list_rate if main_item.combine_price_list_rate else 0.0
			main_item.combine_discount = (flt(main_item.combine_original_rate- main_item.combine_rate)) * 100 / main_item.combine_original_rate if main_item.combine_original_rate else 0.0

@frappe.whitelist()
def ps_before_save(self,method):
	mapping_sales_order(self)

@frappe.whitelist()
def po_before_save(self, method):
	data = frappe.get_list("Product Bundle", fields='new_item_code')
	item_list = [d.new_item_code for d in data]

	for row in self.items:
		if row.item_code in item_list:
			frappe.throw(_("Cannot select Product Bundle item in row {}".format(row.idx)))

		if row.rate and not row.original_rate:
			row.original_rate = row.rate

	tax_breakup_data(self)
	sales_order_ref(self)

def mapping_sales_order(self):
	data = frappe.db.get_value("Delivery Note Item" , {'parent': self.delivery_note}, 'against_sales_order')
	for row in self.items:
		row.db_set('against_sales_order' , data)

def tax_breakup_data(self):
	if self.meta.get_field("other_charges_calculation_qty"):
		# HSN Wise Qty in Sales Invoice
		self.other_charges_calculation_qty = get_tax_breakup_html(self, 1)

	if self.meta.get_field("item_wise_tax_calculation"):
		# HSN Wise Qty in Sales Invoice
		self.item_wise_tax_calculation = get_tax_breakup_html(self)

def get_tax_breakup_html(self, hsn=0):

	if not self.taxes:
		return

	# get headers
	tax_accounts = []
	for tax in self.taxes:
		if getattr(tax, "category", None) and tax.category=="Valuation":
			continue
		if tax.description not in tax_accounts:
			tax_accounts.append(tax.description)

	if hsn:
		headers = get_itemised_tax_breakup_header(self.doctype + " Item", tax_accounts, hsn)
		itemised_tax, itemised_taxable_amount = get_itemised_tax_breakup_data(self, hsn)
	else:
		headers = get_itemised_tax_breakup_header(self.doctype + " Item", tax_accounts)
		itemised_tax, itemised_taxable_amount = get_itemised_tax_breakup_data(self)

	#frappe.msgprint(str(itemised_taxable_amount))
	return frappe.render_template(
		"eie/templates/includes/tax_breakup_data.html", dict(
			headers=headers,
			itemised_tax=itemised_tax,
			itemised_taxable_amount=itemised_taxable_amount,
			tax_accounts=tax_accounts,
			company_currency=erpnext.get_company_currency(self.company)
		)
	)

def get_itemised_tax_breakup_header(item_doctype, tax_accounts, hsn=0):
	if hsn:
		return [_("HSN/SAC"), _("Qty"), _("Taxable Amount")] + tax_accounts
	else:
		return [_("Item"), _("Qty"), _("Taxable Amount")] + tax_accounts

def get_itemised_tax_breakup_data(doc, hsn=0):
	from erpnext.controllers.taxes_and_totals import get_itemised_tax, get_itemised_taxable_amount

	if not hsn:
		itemised_tax = get_itemised_tax(doc.taxes)
		itemised_taxable_amount = get_taxable_amount(doc.items)
		return itemised_tax, itemised_taxable_amount

	itemised_tax = get_itemised_tax(doc.taxes)
	itemised_taxable_amount = get_itemised_taxable_amount(doc.items)
	itemised_taxable_qty = get_itemised_taxable_qty(doc.items)

	if not frappe.get_meta(doc.doctype + " Item").has_field('gst_hsn_code'):
		return itemised_tax, itemised_taxable_amount

	item_hsn_map = frappe._dict()
	for d in doc.items:
		item_hsn_map.setdefault(d.item_code or d.item_name, d.get("gst_hsn_code"))

	hsn_tax = {}
	for item, taxes in itemised_tax.items():
		hsn_code = item_hsn_map.get(item)
		hsn_tax.setdefault(hsn_code, frappe._dict())
		for tax_account, tax_detail in taxes.items():
			hsn_tax[hsn_code].setdefault(tax_account, {"tax_rate": 0, "tax_amount": 0})
			hsn_tax[hsn_code][tax_account]["tax_rate"] = tax_detail.get("tax_rate")
			hsn_tax[hsn_code][tax_account]["tax_amount"] += tax_detail.get("tax_amount")

	# set taxable amount
	hsn_taxable_amount = frappe._dict()
	for item, taxable_amount in itemised_taxable_amount.items():
		hsn_code = str(item_hsn_map.get(item))
		hsn_taxable_amount.setdefault(hsn_code, 0)
		hsn_taxable_amount[hsn_code] += itemised_taxable_amount.get(item)
		hsn_taxable_amount.setdefault(hsn_code + "_qty", 0)
		hsn_taxable_amount[hsn_code + "_qty"] += itemised_taxable_qty.get(item)

	return hsn_tax, hsn_taxable_amount

def get_taxable_amount(items):
	itemised_taxable_amount = frappe._dict()
	for item in items:
		item_code = item.item_code or item.item_name
		itemised_taxable_amount.setdefault(item_code, 0)
		itemised_taxable_amount[item_code] += item.net_amount
		itemised_taxable_amount.setdefault(item_code + '_qty', 0)
		itemised_taxable_amount[item_code + '_qty'] += item.qty

	return itemised_taxable_amount

def get_itemised_taxable_qty(items):
	itemised_taxable_qty = frappe._dict()
	for item in items:
		item_code = item.item_code or item.item_name
		itemised_taxable_qty.setdefault(item_code, 0)
		itemised_taxable_qty[item_code] += item.qty

	return itemised_taxable_qty

@frappe.whitelist()
def get_warehouses(items, factory, company):
	items = json.loads(items)

	warehouses = [factory]
	is_group = frappe.db.get_value("Warehouse", factory, "is_group")
	
	loop = False
	if is_group:
		loop = True
		group = [factory]
	
	while loop:
		warehouse_group = []
		for d in group:
			warehouse_list = frappe.db.get_values('Warehouse',{"parent_warehouse": d, "company": company}, ["name", "is_group"], as_dict=1)
			
			for w in warehouse_list:
				warehouses.append(w.name)
				if w.is_group:
					warehouse_group.append(w.name)
		
		if warehouse_group:
			group = warehouse_group
		else:
			loop = False

	item_warehouse = frappe._dict()
	for row in items:
		if not row.get('item_code'):
			frappe.throw(_("No Item Code found in row {}".format(row['idx'])))

		item_warehouse.setdefault(row['item_code'], '')

		bins = frappe.get_list("Bin", filters={'item_code': row['item_code'], 'actual_qty': ['!=', 0.0]}, fields=('warehouse', 'actual_qty'), order_by='actual_qty desc, modified desc')

		for b in bins:
			if b.warehouse in warehouses:
				item_warehouse.update({row['item_code']: b.warehouse})
				break

	return item_warehouse
	
def sales_order_ref(self):
	for row in self.items:
		so = frappe.db.get_value("Sales Order Item",{ 'parent':row.sales_order,'item_code':row.item_code}, 'qty')
		if so:
			if row.qty > so:
				row.db_set('sales_order_item','')

@frappe.whitelist()
def create_purchase_order_daily():
	data = db.get_list("Material Request", fields = 'name', filters = {
		"company" : "EIE Instruments Pvt. Ltd.",
		"docstatus" : 1 ,
		"status": ['not in', ["Stopped","Ordered"]],
		"schedule_date": ['>=', nowdate()]
	})

	supplier = 'Vindish Instruments Pvt. Ltd.'
	po = frappe.new_doc("Purchase Order")
	po.supplier = supplier

	for row in data:
		doc = frappe.get_doc("Material Request" , row.name)
		for item in doc.items:
			if not frappe.db.exists({"doctype":"Purchase Order Item" , "material_request_item" : item.name}) and item.default_supplier == supplier:

				new_item = frappe._dict({
					'item_code': item.item_code,
					'item_name': item.item_name,
					'default_supplier': supplier,
					'schedule_date': item.schedule_date,
					'description': item.description,
					'qty': item.qty,
					'uom': item.uom,
					'stock_uom': item.stock_uom,
					'warehouse': item.warehouse,
					'item_group': item.item_group,
					'sales_order': item.sales_order,
					'sales_order_item': item.sales_order_item,
					'material_request_item': item.name, 
					'material_request': doc.name, 
					'bom': ''})

				if item.schedule_date < getdate():
					new_item.update({'schedule_date': getdate()})

				min_qty = db.get_value("Item", item.item_code, 'min_order_qty')
				if min_qty > item.qty:
					new_item.update({'qty': min_qty})

				po.append('items',new_item)

	po.insert()
	po.save()
	db.commit()

@frappe.whitelist()
def make_invoice(source_name, target_doc=None):
	doclist = get_mapped_doc("Maintenance Visit", source_name, {
			"Maintenance Visit":{
				"doctype": "Sales Invoice",
				"field_no_map":[
					"naming_series"
				]
			},
			"Maintenance Visit Purpose": {
				"doctype": "Sales Invoice Item"
			}
	}, target_doc)
	
	return doclist

@frappe.whitelist()
def make_maintenance_visit(source_name, target_doc=None):
	def postprocess(source, target):
		target.append('purposes',{
			'item_code': source.item_code,
			'item_name': source.item_name,
			'description': source.item_description	
		})

	doclist = get_mapped_doc("Issue" , source_name,{
			"Issue" :{ 
				"doctype":"Maintenance Visit" , 
				"field_map":{ 
					"name":"from_issue" 
				}, 
				"field_no_map":[
					"naming_series"
				]
			}
		},target_doc, postprocess)

	return doclist

@frappe.whitelist()
def make_quotation(source_name , target_doc=None):
	def postprocess(source, target):
		target.append('items',{
			'item_code': source.item_code,
			'item_name': source.item_name,
			'description': source.item_description	
		})
	doclist = get_mapped_doc("Issue" , source_name,{
			"Issue": {
				"doctype":"Quotation" ,
				"field_no_map":[
					"naming_series"
				]
			}
		},target_doc, postprocess)

	return doclist

@frappe.whitelist()
def emd_sd_mail():
	if getdate().weekday() == 6 and getdate().isocalendar()[1] % 2 == 0:
		enqueue(send_emd_reminder, queue='long', timeout=5000, job_name='EMD Mails')
		enqueue(send_sd_reminder, queue='long', timeout=5000, job_name='SD Mails')
		return "SMD SD Mails Send"

@frappe.whitelist()
def sales_invoice_mails():
	if getdate().weekday() == 6 and getdate().isocalendar()[1] % 2 == 1:
		enqueue(send_sales_invoice_mails, queue='long', timeout=5000, job_name='Payment Reminder Mails')
		return "Payment Reminder Mails Send"

@frappe.whitelist()
def send_sales_invoice_mails():
	from frappe.utils import fmt_money

	def show_progress(status, customer, invoice):
		frappe.publish_realtime(event="cities_progress", message={'status': status, 'customer': customer, 'invoice': invoice}, user=frappe.session.user)

	def header(customer):
		return """<strong>""" + customer + """</strong><br><br>Dear Sir,<br><br>
		Kind attention account department.<br>
		We wish to invite your kind immediate attention to our following bill/s which have remained unpaid till date and are overdue for payment.<br>
		<div align="center">
			<table border="1" cellspacing="0" cellpadding="0" width="100%">
				<thead>
					<tr>
						<th width="16%" valign="top">Bill No</th>
						<th width="12%" valign="top">Bill Date</th>
						<th width="21%" valign="top">Order No</th>
						<th width="15%" valign="top">Order Date</th>
						<th width="16%" valign="top">Actual Amt</th>
						<th width="18%" valign="top">Rem. Amt</th>
					</tr></thead><tbody>"""

	def table_content(name, posting_date, po_no, po_date, rounded_total, outstanding_amount):
		posting_date = posting_date.strftime("%d-%m-%Y") if bool(posting_date) else '-'
		po_date = po_date.strftime("%d-%m-%Y") if bool(po_date) else '-'

		rounded_total = fmt_money(rounded_total, 2, 'INR')
		outstanding_amount = fmt_money(outstanding_amount, 2, 'INR')

		return """<tr>
				<td width="16%" valign="top"> {0} </td>
				<td width="12%" valign="top"> {1} </td>
				<td width="21%" valign="top"> {2} </td>
				<td width="15%" valign="top"> {3} </td>
				<td width="16%" valign="top" align="right"> {4} </td>
				<td width="18%" valign="top" align="right"> {5} </td>
			</tr>""".format(name, posting_date, po_no or '-', po_date, rounded_total, outstanding_amount)
	
	def footer(actual_amount, outstanding_amount):
		actual_amt = fmt_money(sum(actual_amount), 2, 'INR')
		outstanding_amt = fmt_money(sum(outstanding_amount), 2, 'INR')
		return """<tr>
					<td width="68%" colspan="4" valign="top" align="right">
						<strong>Net Receivable &nbsp; </strong>
					</td>
					<td align="right" width="13%" valign="top">
						<strong> {} </strong>
					</td>
					<td align="right" width="18%" valign="top">
						<strong> {} </strong>
					</td>
				</tr></tbody></table></div><br>
				We request you to look into the matter and release the payment/s without Further delay. <br><br>
				If you need any clarifications for any of above invoice/s, please reach out to our Accounts Receivable Team by sending email to cd@eieinstruments.com or call Mr. Mahesh Parmar (079-66040638) or Mr. Hardik Suthar (07966040641).<br><br>
				We will appreciate your immediate response in this regard.<br><br>
				<span style="background-color: rgb(255, 255, 0);">If payment already made from your end, kindly excuse us for this mail with the details of payments made to enable us to reconcile and credit your account. In case of online payment, sometimes, it is difficult to reconcile the name of the Payer and credit the relevant account.<br><br>
				If invoice is not due please reconcile the same and arrange to release on due date. </span><br><br>
				Thanking you in anticipation.<br><br>For, EIE INSTRUMENTS PVT. LTD.<br>( Accountant )""".format(actual_amt, outstanding_amt)

	non_customers = ('Psp Projects Ltd.', 'EIE Instruments Pvt. Ltd.', 'Vindish Instruments Pvt. Ltd.')

	data = frappe.get_list("Sales Invoice", filters={
			'status': ['in', ('Unpaid', 'Overdue')],
			'currency': 'INR',
			'docstatus': 1,
			'dont_send_email': 0,
			'customer': ['not in', non_customers],
			'company': 'EIE Instruments Pvt. Ltd.'},
			order_by='posting_date',
			fields=["name", "customer", "posting_date", "po_no", "po_date", "rounded_total", "outstanding_amount", "contact_email", "naming_series"])

	def get_customers():
		customers_list = list(set([d.customer for d in data if d.customer]))
		customers_list.sort()

		for customer in customers_list:
			yield customer

	def get_customer_si(customer):
		for d in data:
			if d.customer == customer:
				yield d

	cnt = 0
	customers = get_customers()

	sender = formataddr(("Collection Department EIEPL", "cd@eieinstruments.com"))
	for customer in customers:
		attachments, outstanding, actual_amount, recipients = [], [], [], []
		table = ''

		# customer_si = [d for d in data if d.customer == customer]
		customer_si = get_customer_si(customer)

		for si in customer_si:
			show_progress('In Progress', customer, si.name)
			name = "Previous Year Outstanding"
			if si.naming_series != "OSINV-":
				name = si.name
				try:
					attachments.append(frappe.attach_print('Sales Invoice', si.name, print_format="EIE Tax Invoice", print_letterhead=True))
				except:
					pass

			table += table_content(name, si.posting_date, si.po_no, si.po_date,
						si.rounded_total, si.outstanding_amount)

			outstanding.append(si.outstanding_amount)
			actual_amount.append(si.rounded_total or 0.0)

			if bool(si.contact_email) and si.contact_email not in recipients:
				recipients.append(si.contact_email)

		message = header(customer) + '' + table + '' + footer(actual_amount, outstanding)
		message += "<br><br>Recipients: " + ','.join(recipients)
		
		try:
			# frappe.sendmail(recipients='harshdeep.mehta@finbyz.tech',
			frappe.sendmail(
				recipients=recipients,
				cc = 'cd@eieinstruments.com',
				subject = 'Overdue Invoices: ' + customer,
				sender = sender,
				message = message,
				attachments = attachments
			)
			
			cnt += 1
			show_progress('Mail Sent', customer, "All")
		except:
			frappe.log_error("Mail Sending Issue", frappe.get_traceback())
			continue

	show_progress('Success', "All Mails Sent", str(cnt))
	frappe.db.set_value("Cities", "CITY0001", "total", cnt)

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
	def postprocess(source, target):
		set_missing_values(source, target)
		if target.get("allocate_advances_automatically"):
			target.set_advances()

	def set_missing_values(source, target):
		target.is_pos = 0
		target.ignore_pricing_rule = 1
		target.flags.ignore_permissions = True
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

		# set company address
		target.update(get_company_address(target.company))
		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))

	def update_item(source, target, source_parent):
		target.amount = flt(source.amount) - flt(source.billed_amt)
		target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = target.amount / flt(source.rate) if (source.rate and source.billed_amt) else source.qty - source.returned_qty

		if source_parent.project:
			target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center")
		if not target.cost_center and target.item_code:
			item = get_item_defaults(target.item_code, target.company)
			target.cost_center = item.get("selling_cost_center") \
				or frappe.db.get_value("Item Group", item.item_group, "default_cost_center")

	doclist = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Sales Invoice",
			"field_map": {
				"party_account_currency": "party_account_currency",
				"payment_terms_template": "payment_terms_template"
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"name": "so_detail",
				"parent": "sales_order",
			},
			"field_no_map":{
				"serial_no":"serial_no"
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.qty and (doc.base_amount==0 or abs(doc.billed_amt) < abs(doc.amount))
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		},
		"Payment Schedule": {
			"doctype": "Payment Schedule",
		},
	}, target_doc, postprocess, ignore_permissions=ignore_permissions)

	return doclist

@frappe.whitelist()
def item_before_rename(self,method, *args, **kwargs):
	specialchars = '[@_!#$\\\\"\'%^&*()<>?/|}{~:]'
	regex = re.compile(specialchars)
	if(regex.search(args[1])):
		frappe.throw("Special characters like <b> < > ? / ; : \' \" { } [ ] | \\ # $ % ^ ( ) * + </b> are not allowed in Item Code! You keep them in Item Name", title="Invalid Characters")

def pe_before_update_after_submit(self, method):
	pass
	#validate_outstanding_amount(self)

@frappe.whitelist()
def pe_on_submit(self, method):
	#validate_outstanding_amount(self)
	
	attachments = []
	recipients = []
	attachments.append(frappe.attach_print('Payment Entry', self.name, print_format="EIE Payment Entry", print_letterhead=True))
	sender = formataddr(("Vasantkumar Parmar", 'vasant@eieinstruments.com'))
	if self.contact_email != None:
		recipients.append(self.contact_email)

	if self.payment_type == 'Receive':
		payment_receipt_alert(self, attachments, sender, recipients)

def payment_receipt_alert(self, attachments, sender, recipients):
	message = """<p> Dear Sir, </p> 
		<p> Thank you very much for payment of {}.
		<p> Please have payment receipt as attached.</p> 
		<p> For any queries, Please get in touch with our contact available with you. </p> 
		<p>Thanks & Regards, <strong>
		<br/> {} <br/> </strong>
		<p>Contact: 7966040646</p>
		<p>Quation Department- 079-66211201 – info@eieinstruments.com</p> 
		<p>Service Department- 079-66040629 – service.eiepl@gmail.com</p> 
		<p>Dispatch Department – 079-66040612- Sonali.eiepl@gmail.com</p> 
		<p>Logistic Department – 7600001423 – logistic@eieinstruments.com</p> 
		<p>Biling Department – 079-66040685 –  billing@eieinstruments.com</p> 
		<strong>{}</strong> </p>""".format(self.remarks.replace('\n', "<br>"), get_fullname(self.modified_by) or "", self.company)

	frappe.sendmail(recipients=recipients,
		subject = 'Payment Receipt: ' + self.party + ' - ' + self.name,
		sender = sender,
		message = message,
		attachments = attachments)


def validate_outstanding_amount(self):
	out_amt = 0
	for row in self.references:
		if row.reference_doctype in ["Purchase Invoice","Sales Invoice"]:
			out_amt = frappe.db.get_value(row.reference_doctype,row.reference_name,'outstanding_amount')
			# if out_amt < 0:
				# frappe.throw(_("Outstanding amount is become negative for {} in row {}".format(row.reference_name,row.idx)))
		if row.reference_doctype in ["Sales Order","Purchase Order"]:
			adv_paid, grand_total = frappe.db.get_value(row.reference_doctype,row.reference_name,['advance_paid','rounded_total'])
			out_amt = flt(grand_total) - flt(adv_paid)
		if out_amt < 0:
			frappe.throw(_("Outstanding amount is become negative for {} in row {}".format(row.reference_name,row.idx)))

@frappe.whitelist()
def make_meetings(source_name, doctype, ref_doctype, target_doc=None):
	def set_missing_values(source, target):
		target.party_type = doctype
		now = now_datetime()
		if ref_doctype == "Meeting Schedule":
			target.scheduled_from = target.scheduled_to = now
		else:
			target.meeting_from = target.meeting_to = now

	def update_contact(source, target, source_parent):
		if doctype == 'Lead':
			if not source.organization_lead:
				target.contact_person = source.lead_name

	doclist = get_mapped_doc(doctype, source_name, {
			doctype: {
				"doctype": ref_doctype,
				"field_map":  {
					'company_name': 'organisation',
					'name': 'party'
				},
				"field_no_map": [
					"naming_series"
				],
				"postprocess": update_contact
			}
		}, target_doc, set_missing_values)

	return doclist

def fetch_item_grouo(self):
	item_group = frappe.db.get_value("Item", self.item_code, "item_group")
	self.db_set("item_group", item_group)


@frappe.whitelist()
def docs_before_naming(self, method):
	from erpnext.accounts.utils import get_fiscal_year

	date = self.get("transaction_date") or self.get("posting_date") or getdate()

	fy = get_fiscal_year(date)[0]
	fiscal = frappe.db.get_value("Fiscal Year", fy, 'fiscal')

	if fiscal:
		self.fiscal = fiscal
	else:
		fy_years = fy.split("-")
		fiscal = fy_years[0][2:] + "-" + fy_years[1][2:]
		self.fiscal = fiscal


@frappe.whitelist()
def update_grand_total(docname):
	doc = frappe.get_doc("BOM",docname)
	total_op_cost = doc.man_power_cost + doc.ancillary_cost + doc.powder_coating + doc.buffing_cost + doc.wire_cutting_cost + doc.laser_cutting_cost + doc.shaping_machine_cost + doc.boring_machine_cost + doc.grinding_machine_cost + doc.teflon_coating_cost + doc.cooling_system_fitting_cost + doc.cnc_machining_cost + doc.hard_chrome_plating_cost + doc.chrome_plating_cost
	doc.db_set('total_operational_cost',flt(total_op_cost))
	doc.db_set("grand_total_cost",flt(doc.total_cost + doc.total_operational_cost))
	doc.db_set('per_unit_cost',flt(doc.total_cost + doc.total_operational_cost)/flt(doc.quantity))



def calculate_total(self):
	total_op_cost = self.man_power_cost + self.ancillary_cost + self.powder_coating + self.buffing_cost + self.wire_cutting_cost + self.laser_cutting_cost + self.shaping_machine_cost + self.boring_machine_cost + self.grinding_machine_cost + self.teflon_coating_cost + self.cooling_system_fitting_cost + self.cnc_machining_cost + self.hard_chrome_plating_cost + self.chrome_plating_cost
	self.db_set('total_operational_cost',flt(total_op_cost))
	self.db_set("grand_total_cost",flt(self.total_cost + self.total_operational_cost))
	self.db_set('per_unit_cost',flt(self.total_cost + self.total_operational_cost)/flt(self.quantity))
	
@frappe.whitelist()
def calibration_mails_daily():
	for days in [335, 350, 362]:
		enqueue(send_calibration_mail, queue='long', timeout=5000, job_name='Calibration Reminder Mails', days=days)
	
	return "Calibration Reminder Mails Send!"

def send_calibration_mail(days):

	def header(person_name, company_name, contact_number, date):
		return """<p> <strong> Kind Attention: {person_name} ({company_name}) ({contact_number}) </strong> </p>
			<p> <strong> Dear Sir / Madam, </strong> </p>
			<p> <strong> Kindly note that the following item(s), of yours, is/are due for Calibration in {date}. </strong> </p>
			<p> <strong> Can you please inform us when you are planning to Calibrate this instruments so that we can schedule our calibration activities at our end. </strong> </p>
			<p> <strong> This reminder mail is sending just to plan at our end so that we can serve our quality services in time. </strong> </p>
			<p> <strong> Please feel free to contact us for any Clarifications. </strong> </p>
			<table border="1" width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse">
			<tbody> <tr>
				<td width="10%">
					<p align="center"> Sr No: </p>
				</td>
				<td width="70%">
					<p align="center"> Instruments Name </p>
				</td>
				<td width="20%">
					<p align="center"> Qty </p>
				</td>
			</tr>""".format(
				person_name = person_name,
				company_name = company_name,
				contact_number = contact_number,
				date = date)

	def table_content(sr_no, instrument_name, qty):
		return """<tr>
			<td width="10%">
				<p align="center"> {sr_no} </p>
			</td>
			<td width="70%">
				<p align="center"> {instrument_name} </p>
			</td>
			<td width="20%">
				<p align="center"> {qty} </p>
			</td> </tr>""".format(
				sr_no = sr_no,
				instrument_name = instrument_name,
				qty = flt(qty))

	def footer():
		return """</tbody> </table>
			<p> <strong> Thanks & Regards, </strong> </p>
			<p> <strong> EIE Instruments Pvt. Ltd. </strong> </p>
			<p style="font-size: 12px;"> B-14/15 Zaveri Industrial Estate, Opp. Shyamvilla Bunglows,
			<br>Kathwada-Singarva Road, Kathwada, Ahmedabad-382430.
			<br>www.eieinstruments.com | csc.eiepl@gmail.com, service.eiepl@gmail.com
			<br>+91 79 66040680, +91 79 66040660 </p>"""

	data = frappe.db.sql("""
		SELECT si.name, si.posting_date, si.customer, si.contact_display, si.contact_mobile, si.contact_email,
			si_item.item_code, si_item.item_name, si_item.qty
		FROM
			`tabSales Invoice` as si LEFT JOIN `tabSales Invoice Item` as si_item on (si_item.parent = si.name)
		WHERE
			si.docstatus = 1 
			and si.dont_send_calibration_reminder = 0 
			and si_item.item_group in ('CALIBRATION - NON NABL', 'CALIBRATION - NABL')
			and DATE_SUB(CURDATE(), interval {} day) = si.posting_date """.format(days), as_dict = True)

	si_dict = dict()

	for row in data:
		key = (row.name, row.contact_display, row.customer, row.contact_mobile, row.contact_email, row.posting_date)
		si_dict.setdefault(key, [])
		si_dict[key].append(row)

	sender = formataddr(("Abdulbasit", "abdulbasit.eiepl@gmail.com"))

	for (invoice_no, person_name, company_name, contact_mobile, contact_email, posting_date), items in si_dict.items():
		table = ""

		recipients = [contact_email]
		date = add_years(posting_date, 1).strftime("%d-%b-%Y")

		for sr_no, row in enumerate(items, start = 1):
			table += table_content(sr_no, row.item_name, row.qty)

		message = header(person_name, company_name, contact_mobile, date) + table + footer()
		# message += "<br>Recipients: " + ','.join(recipients)
		message += "<br>Invoice No: " + invoice_no

		try:
			# frappe.sendmail(recipients=['harshdeep.mehta@finbyz.tech', 'it@eieinstruments.com'],
			frappe.sendmail(recipients=recipients,
				subject = 'REMINDER FOR CALIBRATION ACTIVITY',
				sender = sender,
				cc = ['abdulbasit.eiepl@gmail.com','service.eiepl@gmail.com'],
				message = message)
		except:
			frappe.publish_realtime(event="cities_progress", message={'status': "FAIL", 'customer': '', 'invoice': ''}, user=frappe.session.user)

def si_validate(self,method):
	check_item_on_validate(self)
	hsn_validation(self)

def so_validate(self,method):
	check_item_on_validate(self)

def dn_validate(self,method):
	check_item_on_validate(self)

def qt_validate(self,method):
	check_item_on_validate(self)

def check_item_on_validate(self):
	if self.company == "EIE Instruments Pvt. Ltd.":
		for row in self.items:
			checked = frappe.db.get_value('Item', row.item_code, 'dont_allow_sales_in_eie')
			if checked == 1:
				frappe.throw(_("Sales is not allowed in EIE for {0}".format(row.item_code)))

def hsn_validation(self):
	for row in self.items:
		if not row.gst_hsn_code:
			frappe.throw(_(f"Row:{row.idx} Please define HSN in Item {row.item_code}"))

@frappe.whitelist()
def send_emd_reminder():
	from frappe.utils import fmt_money
	
	def header(customer, address_display, contact_display):
		message = """
		<center><strong>E.M.D. Reminder</strong></center>
		<strong>{}</strong><br><br>
		{}
		<br><br>
		<strong>Attn.: {}</strong><br><br>
		<strong>Sub.: Refund of E.M.D.</strong><br><br>

		Dear Sir<br><br>
		May we invite your kind immediate attention to our following E.M.D./s which may please be refunded in  case the tender/s have been finalised.<br><br>

		<div>
			<table border="1" cellspacing="0" cellpadding="0" width="100%" align="center">
				<thead>
					<tr>
						<th align="left" width="20%">Tender No</th>
						<th align="left" width="15%">Due Date</th>
						<th align="left" width="10%">EMD Amount</th>
						<th align="left" width="8%">Pay Mode</th>
						<th align="left" width="8%">Inst. No</th>
						<th align="left" width="8%">Bank Name</th>
						<th align="left" width="31%">Tender Name</th>
					</tr>
				</thead>
				<tbody>
		""".format(customer or '', address_display or '', contact_display or '')
		return message

	def table_content(tender_no, due_date, amount, payment_mode, reference_num, bank_account, tender_name):
		
		message = """
					<tr>
						<td>{}</td>
						<td>{}</td>
						<td align="right">{}</td>
						<td>{}</td>
						<td>{}</td>
						<td>{}</td>
						<td>{}</td>
					</tr>
		""".format(tender_no or '-', due_date or '', amount, payment_mode or '', reference_num or '', bank_account or '', tender_name or '')
		return message
	def footer(actual_amount, company):
		message = """
				</tbody>
			</table><br>
			<center><strong>TOTAL </strong> : {}</center><br><br>

			We request for your immediate actions in this regards. <br><br>
			If you need any clarifications for any of above invoice/s, please reach out to our Accounts Receivable Team by sending email to tender@eieinstruments.com Or Call Ms. Sadhna Patel (079-66211215) or call Mr. Mahesh Parmar (079-66040638) . <br><br>
			If refund already made from your end, kindly excuse us for this mail with the details of payments made to enable us to reconcile and credit your account. In case of online payment, sometimes, it is difficult to reconcile the name of the Payer and credit the relevant account. <br><br><br>
			Thanking you in anticipation. <br><br><br>
			<strong>For, {}</strong><br>
			( Accountant )
		</div>

		""".format(sum(actual_amount), company)
		return message

	data = frappe.get_list("EMD", filters={
		'due_date': ("<=", add_days(nowdate())),
		'returned': 0,
		'dont_send_email': 0,
		'deposit_account': ["like","%EMD Receivable%"],
		'docstatus': 1
		},
		order_by='posting_date',
		fields=["customer", "address_display", "contact_display", "tender_no", "due_date", "amount", "payment_mode", "reference_num", "bank_account", "tender_name", "company", "contact_email"]
	)

	def get_customers():
		customers_list = list(set([d.customer for d in data if d.customer]))
		customers_list.sort()

		for customer in customers_list:
			yield customer

	def get_customer_emd(customer):
		for d in data:
			if d.customer == customer:
				yield d
	
	cnt = 0
	customers = get_customers()

	sender = formataddr(("Tender", "tender@eieinstruments.com"))
	for customer in customers:
		attachments, outstanding, actual_amount, recipients = [], [], [], []
		table = ''

		# customer_si = [d for d in data if d.customer == customer]
		# get_customer_emd = get_customer_emd(customer)

		for si in get_customer_emd(customer):
			# name = "EID Outstanding"
			
			table += table_content(si.tender_no, si.due_date, si.amount, si.payment_mode, si.reference_num, si.bank_account, si.tender_name)
			address_display = si.address_display
			company = si.company
			contact_display = si.contact_display
			# outstanding.append(si.amount)
			actual_amount.append(si.amount or 0.0)

			if bool(si.contact_email) and si.contact_email not in recipients:
				recipients.append(si.contact_email)

		message = header(customer, address_display, contact_display) + '' + table + '' + footer(actual_amount, company)
		# message += "<br><br>Recipients: " + ','.join(recipients)
		
		try:
			frappe.sendmail(
				recipients=recipients,
				subject = 'REFUND / RELEASE OF SECURITY DEPOSIT',
				sender = sender,
				cc = ['tender@eieinstruments.com'],
				message = message,
				attachments = attachments
			)
			cnt += 1
		except:
			frappe.log_error("Mail Sending Issue", frappe.get_traceback())
			continue
	pass

@frappe.whitelist()
def validate_material_request(sales_order):
	try:
		material_request = frappe.db.sql(f"""
		SELECT
			parent
		FROM
			`tabMaterial Request Item`
		WHERE
			parenttype="Material Request" and sales_order = '{sales_order}'
	""")
	except KeyError:
		material_request = None
	if material_request:
		status = frappe.db.get_value("Material Request",material_request[0][0],"docstatus")
		return status
		if status != 2:
			frappe.throw(_("Cancel Material Request of this Sales Order"))
			return "Cancel Material Request of this Sales Order"

@frappe.whitelist()
def send_sd_reminder():
	from frappe.utils import fmt_money
	
	def header(customer, address_display, contact_display):
		message = """
		<center><strong>S.D. Reminder</strong></center><br>
		<strong>{}</strong><br><br>
		{}
		<br><br>
		<strong>Attn.: {}</strong><br><br>
		<strong>Sub.: Refund of S.D.</strong><br><br>

		Dear Sir<br><br>
		We wish to invite your attention to our following Security Deposits,  which may please be refunded to us since we have already executed the contract to your satisfaction.
		<br><br>
		<div>
			<table border="1" cellspacing="0" cellpadding="0" width="100%" align="center">
				<thead>
					<tr>
						<th align="left" width="25%">P.O No</th>
						<th align="left" width="15%">Ref Date</th>
						<th align="left" width="15%">Due Date</th>
						<th align="left" width="10%">S.D. Amount</th>
						<th align="left" width="15%">Payee Bank</th>
						<th align="left" width="10%">Instrument No</th>
						<th align="left" width="10%">O/S Amount</th>
					</tr>
				</thead>
				<tbody>
		""".format(customer or '', address_display or '', contact_display or '')
		return message

	def table_content(tender_no, ref_date, due_date, amount, payment_mode, reference_num, bank_account):
		
		message = """
					<tr>
						<td>{}</td>
						<td>{}</td>
						<td>{}</td>
						<td align="right">{}</td>
						<td>{}</td>
						<td>{}</td>
						<td align="right">{}</td>
					</tr>
		""".format(tender_no or '', ref_date or '',due_date or '', amount or  '', bank_account or '', reference_num or  '', amount or  '')
		return message
	def footer(actual_amount, company):
		message = """
				</tbody>
			</table><br>
			<center><strong>TOTAL </strong> : {}</center><br><br>

			We request for your immediate actions in this regards. <br><br>
			If you need any clarifications for any of above invoice/s, please reach out to our Accounts Receivable Team by sending email to tender@eieinstruments.com Or Call Ms. Sadhna Patel (079-66211215) or call Mr. Mahesh Parmar (079-66040638).<br><br>
			If refund already made from your end, kindly excuse us for this mail with the details of payments made to enable us to reconcile and credit your account. In case of online payment, sometimes, it is difficult to reconcile the name of the Payer and credit the relevant account. <br><br><br>
			Thanking you in anticipation. <br><br><br>
			<strong>For, {}</strong><br>
			( Accountant )
		</div>

		""".format(sum(actual_amount), company)
		return message

	data = frappe.get_list("EMD", filters={
		'due_date': ("<=", add_days(nowdate())),
		'returned': 0,
		'dont_send_email': 0,
		'deposit_account': ["like","%SD Receivable%"],
		'docstatus': 1,
		'name': 'EMD-00863'
		},
		order_by='posting_date',
		fields=["customer", "address_display", "address_display", "tender_no", "due_date", "amount", "payment_mode", "reference_num", "bank_account", "tender_name", "company", "posting_date", "reference_date", "contact_email"]
	)

	def get_customers():
		customers_list = list(set([d.customer for d in data if d.customer]))
		customers_list.sort()

		for customer in customers_list:
			yield customer

	def get_customer_emd(customer):
		for d in data:
			if d.customer == customer:
				yield d
	
	cnt = 0
	customers = get_customers()

	sender = formataddr(("Tender", "tender@eieinstruments.com"))
	for customer in customers:
		attachments, outstanding, actual_amount, recipients = [], [], [], []
		table = ''

		# customer_si = [d for d in data if d.customer == customer]
		# get_customer_emd = get_customer_emd(customer)

		for si in get_customer_emd(customer):
			# name = "EID Outstanding"
			
			table += table_content(si.tender_no, si.reference_date, si.due_date, si.amount, si.payment_mode, si.reference_num, si.bank_account)

			# outstanding.append(si.amount)
			actual_amount.append(si.amount or 0.0)
			company = si.company
			contact_display = si.contact_display
			address_display = si.address_display
			if bool(si.contact_email) and si.contact_email not in recipients:
				recipients.append(si.contact_email)

		message = header(customer, address_display, contact_display) + '' + table + '' + footer(actual_amount, company)
		# message += "<br><br>Recipients: " + ','.join(recipients)
		
		try:
			# frappe.sendmail(recipients='harshdeep.mehta@finbyz.tech',
			frappe.sendmail(
				recipients=recipients,
				subject = 'REFUND / RELEASE OF SECURITY DEPOSIT',
				sender = sender,
				cc = ['tender@eieinstruments.com'],
				message = message,
				attachments = attachments,
			)
			
			cnt += 1
		except:
			frappe.log_error("Mail Sending Issue", frappe.get_traceback())
			continue
	pass

@frappe.whitelist()
def make_stock_entry(work_order_id, purpose, qty=None):
	#from erpnext.stock.doctype.stock_entry.stock_entry import get_additional_costs
	work_order = frappe.get_doc("Work Order", work_order_id)
	if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
		wip_warehouse = work_order.wip_warehouse
	else:
		wip_warehouse = None

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = purpose
	stock_entry.work_order = work_order_id
	stock_entry.company = work_order.company
	stock_entry.from_bom = 1
	stock_entry.bom_no = work_order.bom_no
	stock_entry.use_multi_level_bom = work_order.use_multi_level_bom
	stock_entry.fg_completed_qty = qty or (flt(work_order.qty) - flt(work_order.produced_qty))
	if work_order.bom_no:
		stock_entry.inspection_required = frappe.db.get_value('BOM',
			work_order.bom_no, 'inspection_required')

	if purpose=="Material Transfer for Manufacture":
		stock_entry.to_warehouse = wip_warehouse
		stock_entry.project = work_order.project
	else:
		stock_entry.from_warehouse = wip_warehouse
		stock_entry.to_warehouse = work_order.fg_warehouse
		stock_entry.project = work_order.project

	stock_entry.set_stock_entry_type()
	get_items(stock_entry)
	return stock_entry.as_dict()
	
	
def get_items(self):
	self.set('items', [])
	self.validate_work_order()

	if not self.posting_date or not self.posting_time:
		frappe.throw(_("Posting date and posting time is mandatory"))

	self.set_work_order_details()

	if self.bom_no:

		if self.purpose in ["Material Issue", "Material Transfer", "Manufacture", "Repack",
				"Send to Subcontractor", "Material Transfer for Manufacture", "Material Consumption for Manufacture"]:

			if self.work_order and self.purpose == "Material Transfer for Manufacture":
				item_dict = self.get_pending_raw_materials()
				if self.to_warehouse and self.pro_doc:
					for item in itervalues(item_dict):
						item["to_warehouse"] = self.pro_doc.wip_warehouse
				self.add_to_stock_entry_detail(item_dict)

			elif (self.work_order and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture")
				and not self.pro_doc.skip_transfer and frappe.db.get_single_value("Manufacturing Settings",
				"backflush_raw_materials_based_on")== "Material Transferred for Manufacture"):
				# frappe.msgprint('get items')
				get_transfered_raw_materials(self)

			elif self.work_order and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture") and \
				frappe.db.get_single_value("Manufacturing Settings", "backflush_raw_materials_based_on")== "BOM" and \
				frappe.db.get_single_value("Manufacturing Settings", "material_consumption")== 1:
				self.get_unconsumed_raw_materials()
			else:
				if not self.fg_completed_qty:
					frappe.throw(_("Manufacturing Quantity is mandatory"))

				item_dict = self.get_bom_raw_materials(self.fg_completed_qty)

				#Get PO Supplied Items Details
				if self.purchase_order and self.purpose == "Send to Subcontractor":
					#Get PO Supplied Items Details
					item_wh = frappe._dict(frappe.db.sql("""
						select rm_item_code, reserve_warehouse
						from `tabPurchase Order` po, `tabPurchase Order Item Supplied` poitemsup
						where po.name = poitemsup.parent
							and po.name = %s""",self.purchase_order))

				for item in itervalues(item_dict):
					if self.pro_doc and (cint(self.pro_doc.from_wip_warehouse) or not self.pro_doc.skip_transfer):
						item["from_warehouse"] = self.pro_doc.wip_warehouse
					#Get Reserve Warehouse from PO
					if self.purchase_order and self.purpose=="Send to Subcontractor":
						item["from_warehouse"] = item_wh.get(item.item_code)
					item["to_warehouse"] = self.to_warehouse if self.purpose=="Send to Subcontractor" else ""

				self.add_to_stock_entry_detail(item_dict)

			if self.purpose != "Send to Subcontractor" and self.purpose in ["Manufacture", "Repack"]:
				scrap_item_dict = self.get_bom_scrap_material(self.fg_completed_qty)
				for item in itervalues(scrap_item_dict):
					if self.pro_doc and self.pro_doc.scrap_warehouse:
						item["to_warehouse"] = self.pro_doc.scrap_warehouse

				self.add_to_stock_entry_detail(scrap_item_dict, bom_no=self.bom_no)

		# fetch the serial_no of the first stock entry for the second stock entry
		if self.work_order and self.purpose == "Manufacture":
			self.set_serial_nos(self.work_order)
			work_order = frappe.get_doc('Work Order', self.work_order)
			add_additional_cost(self, work_order)

		# add finished goods item
		if self.purpose in ("Manufacture", "Repack"):
			self.load_items_from_bom()

	self.set_actual_qty()
	self.calculate_rate_and_amount(raise_error_if_no_rate=False)
	
def get_transfered_raw_materials(self):
	# frappe.msgprint('inside get_transfered_raw_materials')
	transferred_materials = frappe.db.sql("""
		select
			item_name, original_item, item_code, qty, sed.t_warehouse as warehouse,
			description, stock_uom, expense_account, cost_center, batch_no
		from `tabStock Entry` se,`tabStock Entry Detail` sed
		where
			se.name = sed.parent and se.docstatus=1 and se.purpose='Material Transfer for Manufacture'
			and se.work_order= %s and ifnull(sed.t_warehouse, '') != ''
	""", self.work_order, as_dict=1)

	materials_already_backflushed = frappe.db.sql("""
		select
			item_code, sed.s_warehouse as warehouse, sum(qty) as qty
		from
			`tabStock Entry` se, `tabStock Entry Detail` sed
		where
			se.name = sed.parent and se.docstatus=1
			and (se.purpose='Manufacture' or se.purpose='Material Consumption for Manufacture')
			and se.work_order= %s and ifnull(sed.s_warehouse, '') != ''
	""", self.work_order, as_dict=1)

	backflushed_materials= {}
	for d in materials_already_backflushed:
		backflushed_materials.setdefault(d.item_code,[]).append({d.warehouse: d.qty})

	po_qty = frappe.db.sql("""select qty, produced_qty, material_transferred_for_manufacturing from
		`tabWork Order` where name=%s""", self.work_order, as_dict=1)[0]

	manufacturing_qty = flt(po_qty.qty)
	produced_qty = flt(po_qty.produced_qty)
	trans_qty = flt(po_qty.material_transferred_for_manufacturing)

	for item in transferred_materials:
		qty= item.qty
		item_code = item.original_item or item.item_code
		req_items = frappe.get_all('Work Order Item',
			filters={'parent': self.work_order, 'item_code': item_code},
			fields=["required_qty", "consumed_qty"]
			)
		# frappe.msgprint('OUT')
		if not req_items:
			# frappe.msgprint('IN')
			wo = frappe.get_doc("Work Order",self.work_order)
			wo.append('required_items',{
				'item_code': item.item_code,
				'source_wareouse': item.items_warehouse
			})
			wo.save()
			req_items = frappe.get_all('Work Order Item',
				filters={'parent': self.work_order,'item_code':item_code},
				fields=["required_qty", "consumed_qty"]
			)
			# frappe.msgprint(_("Did not found transfered item {0} in Work Order {1}, the item not added in Stock Entry")
				# .format(item_code, self.work_order))
			# continue

		req_qty = flt(req_items[0].required_qty)
		req_qty_each = flt(req_qty / manufacturing_qty)
		consumed_qty = flt(req_items[0].consumed_qty)

		if trans_qty and manufacturing_qty >= (produced_qty + flt(self.fg_completed_qty)):
			# if qty >= req_qty:
			# 	qty = (req_qty/trans_qty) * flt(self.fg_completed_qty)
			# else:
			qty = qty - consumed_qty

			if self.purpose == 'Manufacture':
				# If Material Consumption is booked, must pull only remaining components to finish product
				if consumed_qty != 0:
					remaining_qty = consumed_qty - (produced_qty * req_qty_each)
					exhaust_qty = req_qty_each * produced_qty
					if remaining_qty > exhaust_qty and req_qty_each:
						if (remaining_qty/(req_qty_each * flt(self.fg_completed_qty))) >= 1:
							qty =0
						else:
							qty = (req_qty_each * flt(self.fg_completed_qty)) - remaining_qty
				# else:
				# 	qty = req_qty_each * flt(self.fg_completed_qty)


		elif backflushed_materials.get(item.item_code):
			for d in backflushed_materials.get(item.item_code):
				if d.get(item.warehouse):
					if (qty > req_qty):
						qty = req_qty
						qty-= d.get(item.warehouse)

		if qty > 0:
			add_to_stock_entry_detail(self, {
				item.item_code: {
					"from_warehouse": item.warehouse,
					"to_warehouse": "",
					"qty": qty,
					"item_name": item.item_name,
					"description": item.description,
					"stock_uom": item.stock_uom,
					"expense_account": item.expense_account,
					"cost_center": item.buying_cost_center,
					"original_item": item.original_item,
					"batch_no": item.batch_no
				}
			})


def add_to_stock_entry_detail(self, item_dict, bom_no=None):
	cost_center = frappe.db.get_value("Company", self.company, 'cost_center')

	for d in item_dict:
		stock_uom = item_dict[d].get("stock_uom") or frappe.db.get_value("Item", d, "stock_uom")

		se_child = self.append('items')
		se_child.s_warehouse = item_dict[d].get("from_warehouse")
		se_child.t_warehouse = item_dict[d].get("to_warehouse")
		se_child.item_code = item_dict[d].get('item_code') or cstr(d)
		se_child.item_name = item_dict[d]["item_name"]
		se_child.description = item_dict[d]["description"]
		se_child.uom = item_dict[d]["uom"] if item_dict[d].get("uom") else stock_uom
		se_child.stock_uom = stock_uom
		se_child.qty = flt(item_dict[d]["qty"], se_child.precision("qty"))
		se_child.expense_account = item_dict[d].get("expense_account")
		se_child.cost_center = item_dict[d].get("cost_center") or cost_center
		se_child.allow_alternative_item = item_dict[d].get("allow_alternative_item", 0)
		se_child.subcontracted_item = item_dict[d].get("main_item_code")
		se_child.original_item = item_dict[d].get("original_item")
		se_child.batch_no = item_dict[d].get("batch_no")

		if item_dict[d].get("idx"):
			se_child.idx = item_dict[d].get("idx")

		if se_child.s_warehouse==None:
			se_child.s_warehouse = self.from_warehouse
		if se_child.t_warehouse==None:
			se_child.t_warehouse = self.to_warehouse

		# in stock uom
		se_child.conversion_factor = flt(item_dict[d].get("conversion_factor")) or 1
		se_child.transfer_qty = flt(item_dict[d]["qty"]*se_child.conversion_factor, se_child.precision("qty"))


		# to be assigned for finished item
		se_child.bom_no = bom_no

def override_after_insert(self):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
	alert_dict = get_alert_dict(self)
	if alert_dict:
		frappe.publish_realtime('energy_point_alert', message=alert_dict, user=self.user)

	frappe.cache().hdel('energy_points', self.user)
	frappe.publish_realtime('update_points', after_commit=True)

	if self.type not in ['Review', 'Revert']:
		reference_user = self.user if self.type == 'Auto' else self.owner
		notification_doc = {
			'type': 'Energy Point',
			'document_type': self.reference_doctype,
			'document_name': self.reference_name,
			'subject': get_notification_message(self),
			'from_user': reference_user,
			'email_content': '<div>{}</div>'.format(self.reason) if self.reason else None
		}

		enqueue_create_notification(self.user, notification_doc)

# def pe_on_submit(self,method):
# 	validate_outstanding_amount(self)

# def validate_outstanding_amount(self):
# 	if self.references:
# 		for row in self.references:
# 			if row.allocated_amount and row.reference_name:
# 				#doc = frappe.get_doc(row.reference_doctype,row.reference_name)
# 				# meta = frappe.get_meta()
# 				#if hasattr(doc,'outstanding_amount'):
# 				if frappe.get_meta(row.reference_doctype).get_field('outstanding_amount'):
# 					#frappe.msgprint('hi')
# 					outstanding_amount = frappe.db.get_value(row.reference_doctype,row.reference_name,'outstanding_amount')
# 					if row.allocated_amount > outstanding_amount:
# 						frappe.throw(_("Row:{0} # You can not allocate more than {1} against {2} <b>{3}</b>").format(row.idx,outstanding_amount,row.reference_doctype,row.reference_name))
						

def validate_outstanding_amount(self):
	if self.references:
		for row in self.references:
			if row.allocated_amount and row.reference_name and row.reference_doctype not in ['Sales Order', 'Purchase Order']:
				total = frappe.db.sql("""
				select sum(credit_in_account_currency-debit_in_account_currency)
				from `tabGL Entry`
				where 
					docstatus=1 and voucher_no ='{0}' and party_type ='{1}' and party='{2}' and (against_voucher is Null or against_voucher='{0}')
				""".format(row.reference_name,self.party_type,self.party))
				if total:
					total_amount = total[0][0]
				else:
					total_amount = 0
				amount_against = frappe.db.get_value("GL Entry",{'against_voucher':row.reference_name,'voucher_no':['not in', [row.reference_name,self.name]]} ,['sum(credit_in_account_currency-debit_in_account_currency)'])
				difference_amount = abs(flt(total_amount))-abs(flt(amount_against)) 
				if flt(row.allocated_amount) > flt(difference_amount):
					frappe.throw(_("Row:{0} # You can not allocate more than {1} against {2} <b>{3}</b>").format(row.idx,abs(difference_amount),row.reference_doctype,row.reference_name))

def se_validate(self,method):
	if self.purpose in ['Repack','Manufacture','Material Issue']:
		self.get_stock_and_rate()
	validate_additional_cost(self)

def validate_additional_cost(self):
	if self.purpose in ['Material Transfer','Material Transfer for Manufacture','Repack','Manufacture'] and self._action == "submit":
		if round(self.value_difference/100,0) != round(self.total_additional_costs/100,0):
			frappe.throw("ValuationError: Value difference between incoming and outgoing amount is higher than additional cost")


def get_full_path(doc):
	"""Returns file path from given file name"""

	file_path = doc.file_url or doc.file_name

	if "/" not in file_path:
		file_path = "/files/" + file_path

	if file_path.startswith("/private/files/"):
		file_path = get_files_path(*file_path.split("/private/files/", 1)[1].split("/"), is_private=1)

	elif file_path.startswith("/files/"):
		file_path = get_files_path(*file_path.split("/files/", 1)[1].split("/"))

	elif file_path.startswith("http"):
		pass

	elif not doc.file_url:
		frappe.throw(_("There is some problem with the file url: {0}").format(file_path))

	return file_path

import os
from frappe.utils import call_hook_method, cint, cstr, encode, get_files_path
def change_url():
	data =frappe.get_list("File",{'is_private':0,'attached_to_doctype':['!=','Item']})
	for idx,d in enumerate(data,start=0):
		doc = frappe.get_doc("File",d.name)

		if doc.file_url and doc.attached_to_doctype != 'Notification Control':
			path = get_full_path(doc)
			if os.path.exists(path):
				if doc.attached_to_name:
					if frappe.db.exists(doc.attached_to_doctype,doc.attached_to_name):
						print(idx, d.name)
						doc.file_name = doc.file_url.split('/')[-1]
						doc.is_private = 1
						doc.save()
						if idx%50 == 0:
							frappe.db.commit()
							print('commit' + str(idx), str(d.name))
				elif not doc.attached_to_name:
					print(idx, d.name)
					doc.file_name = doc.file_url.split('/')[-1]
					doc.is_private = 1
					doc.save()
					if idx%50 == 0:
						frappe.db.commit()
						print('commit' + str(idx), str(d.name))

