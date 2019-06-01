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
from frappe.utils import nowdate, get_url_to_form, flt, cstr, getdate, get_fullname, now_datetime, parse_val
from frappe.model.mapper import get_mapped_doc
from frappe.utils.background_jobs import enqueue
from email.utils import formataddr
from frappe.core.doctype.communication.email import make

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

@frappe.whitelist()
def IP_before_save(self,method):
	fetch_item_grouo(self)

@frappe.whitelist()
def SE_before_save(self,method):
	update_serial_no(self, method)

@frappe.whitelist()
def customer_before_save(self,method):
	update_industry(self)
	
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
			'po_detail': item.purchase_order_item
		})

	pi.taxes_and_charges = self.taxes_and_charges
	pi.shipping_rule = self.shipping_rule
	pi.shipping_address = self.shipping_address_name
	pi.shipping_address_display = self.shipping_address
	pi.tc_name = 'Purchase Terms'

	old_abbr = db.get_value("Company", self.company, 'abbr')
	new_abbr = db.get_value("Company", self.customer, 'abbr')

	for tax in self.taxes:
		account_head = tax.account_head.replace(old_abbr, new_abbr)
		if not db.exists("Account", account_head):
			frappe.msgprint(_("The Account Head <b>{0}</b> does not exists. Please create Account Head for company <b>{1}</b> and create Purchase Invoice manually.".format(_(account_head), _(self.customer))), title="Purchase Invoice could not be created", indicator='red')
			return

		pi.append('taxes',{
				'charge_type': tax.charge_type,
				'account_head': tax.account_head.replace(old_abbr, new_abbr),
				'rate': tax.rate,
				'description': tax.description.replace(old_abbr, '')
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
			frappe.msgprint(_("The Account Head <b>{0}</b> does not exists. Please create Account Head for company <b>{1}</b> and create Purchase Order manually.".format(_(account_head), _(self.customer))), title="Purchase Order could not be created", indicator='red')
			return

		so.append('taxes',{
				'charge_type': tax.charge_type,
				'account_head': account_head,
				'rate': tax.rate,
				'description': tax.description.replace(old_abbr, '')
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
				'account_head': account_head,
				'rate': tax.rate,
				'description': tax.description.replace(old_abbr, ''),
				'cost_center': cost_center
			})

	pr.tc_name = 'Purchase Terms'
	try:
		pr.save()
		# time.sleep(1)
		# pr.submit()
	except Exception as e:
		frappe.throw(_(e))
	else:
		self.db_set('purchase_receipt', pr.name)
		db.commit()

	url = get_url_to_form("Purchase Receipt", pr.name)

	# frappe.msgprint(_("Purchase Receipt <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=pr.name)), title="Purchase Receipt Created", indicator="green")
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


def new_item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	conditions = []

	return db.sql("""
		select
			tabItem.name, tabItem.item_other_names, tabItem.item_group
		from
			tabItem
		where 
			tabItem.docstatus < 2
			and tabItem.has_variants=0
			and tabItem.disabled=0
			and (tabItem.end_of_life > %(today)s or ifnull(tabItem.end_of_life, '0000-00-00')='0000-00-00')
			and (tabItem.`{key}` LIKE %(txt)s
				or tabItem.item_name LIKE %(txt)s
				or tabItem.item_group LIKE %(txt)s
				or tabItem.item_other_names LIKE %(txt)s
				or tabItem.barcode LIKE %(txt)s)
			{fcond} {mcond}
		order by
			default_selection desc,
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, item_name), locate(%(_txt)s, item_name), 99999) 
		limit %(start)s, %(page_len)s """.format(
			key=searchfield,
			fcond=get_filters_cond(doctype, filters, conditions).replace('%', '%%'),
			mcond=get_match_cond(doctype).replace('%', '%%')),
			{
				"today": nowdate(),
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


@frappe.whitelist()
def qt_before_save(self, method):
	calculate_combine(self)


def calculate_combine(self):
	main_item_object_dict = {}
	main_item_dict = {}

	count = 0
	for row in self.items:
		if row.discount_per:
			disc = flt(row.original_rate) * flt(row.discount_per) / 100.0
			rate = flt(row.original_rate) - disc
			row.rate = rate

		if not row.price_list_rate:
			row.price_list_rate = row.rate

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
def sales_invoice_mails():
	# if getdate().weekday() == 6 and getdate().isocalendar()[1] % 2 == 0:
	if getdate().weekday() == 1 and getdate().isocalendar()[1] % 2 == 1:
		enqueue(send_sales_invoice_mails, queue='long', timeout=8000, job_name='Payment Reminder Mails')
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
				<span style="background-color: rgb(255, 255, 0);">Please ignore this mail if payment is already done.<br><br>
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

	# data = frappe.get_list("Sales Invoice", filters={
	# 	'name': "EP/18-19/5807"},
	# 	fields=["name", "customer", "posting_date", "po_no", "po_date", "rounded_total", "outstanding_amount", "contact_email", "naming_series"])

	customers = list(set([d.customer for d in data if d.customer]))
	customers.sort()
	cnt = 0
	sender = formataddr(("Collection Department EIEPL", "cd@eieinstruments.com"))
	for customer in customers:
		attachments, outstanding, actual_amount, recipients = [], [], [], []
		table = ''

		customer_si = [d for d in data if d.customer == customer]

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
			frappe.sendmail(recipients=recipients,
				cc = 'cd@eieinstruments.com',
				subject = 'Overdue Invoices: ' + customer,
				sender = sender,
				message = message,
				attachments = attachments)
			
			cnt += 1
			show_progress('Mail Sent', customer, "All")
		except:
			frappe.log_error("Mail Sending Issue", frappe.get_traceback())
			continue

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

@frappe.whitelist()
def pe_on_submit(self, method):
	attachments = []
	recipients = []
	attachments.append(frappe.attach_print('Payment Entry', self.name, print_format="EIE Payment Entry", print_letterhead=True))
	sender = formataddr(("Vasantkumar Parmar", 'vasant@eieinstruments.com'))
 	if self.contact_email != None:
	 	recipients.append(self.contact_email)

	if self.payment_type == 'Receive':
		payment_receipt_alert(self, attachments, sender, recipients)
	# elif self.payment_type == 'Pay':
	# 	if self.mode_of_payment == 'Cheque':
	# 		payment_advice_cheque(self, attachments, sender, recipients)
	# 	else:
	# 		payment_advice(self, attachments, sender, recipients)

def payment_receipt_alert(self, attachments, sender, recipients):
	message = """<p> Dear Sir, </p> <p> Thank you very much for payment of {}.<p> Please have payment receipt as attached.</p> <p> For any queries, Please get in touch with our contact available with you. </p> <p>
		Thanks & Regards, <strong> <br/> {} <br/> </strong><p>Contact: 7966040646</p>  <strong>{}</strong> </p>""".format(self.remarks.replace('\n', "<br>"), get_fullname(self.modified_by) or "", self.company)

	frappe.sendmail(recipients=recipients,
		subject = 'Payment Receipt: ' + self.party + ' - ' + self.name,
		sender = sender,
		message = message,
		attachments = attachments)

def payment_advice_cheque(self, attachments, sender, recipients):
	message = """<p>Dear Sir,</p><br><p>Your Cheque is ready against your outstanding %s – Please Pick-up your cheque tomorrow between 02:00 PM To 06:00 PM</p>
	<br><p>Address :</br>Eie Instruments Pvt Ltd</br>B 14 15 16 Zaveri Industrial Estate,</br>
	Singarwa – Kathwada Road,</br> Kathwada, Ahmedabad – 382430</br>Ph no: 079-66040660</p>	"""% (self.get_formatted('paid_amount') or '')

	frappe.sendmail(recipients=recipients,
		subject = 'Payment Advice: ' + self.party + ' - ' + self.name,
		sender = sender,
		cc = ['vasant@eieinstruments.com'],
		message = message,
		attachments = attachments)

def payment_advice(self, attachments, sender, recipients):
	message = """<p>Dear Sir/Madam,</p><p>This is to advise you that an amount Rs. {} is being credited by {} to your  Bank Account.</p><p>We have deposited cheque of {}.<p>
	Please have payment receipt as attached.</p><p>
	If you have any Queries on the payment , Please do not hesitate to Contact.
	And if any Bills are Still Outstanding Please mail us :
	<a href="mailto:vasant@eieinstruments.com" target="_blank">
		vasant@eieinstruments.com</a></p><p>
	If you not receive the amount in couple of the days, Please Inform Us
	immediately then we will not responsible for any matter.
	</p><p>Thanks &amp; Regards,<strong><br/>{}	<br/></strong>
	<strong>{}</strong></p>""".format(self.get_formatted('paid_amount'), self.mode_of_payment, self.remarks.replace('\n', "<br>"), get_fullname(self.modified_by) or "", self.company)
	
	frappe.sendmail(recipients=recipients,
		subject = 'Payment Advice: ' + self.party + ' - ' + self.name,
		sender = sender,
		cc = ['vasant@eieinstruments.com'],
		message = message,
		attachments = attachments)

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
def cities():
	pass

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
		
def update_industry(self):
	if self.lead_name:
		lead = frappe.get_doc("Lead",self.lead_name)
		lead.industry = self.industry
		lead.save()
		
	frappe.db.commit()
		
