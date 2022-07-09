import frappe, json
from frappe import _, bold
from frappe.utils import cstr, cint, flt, getdate, format_date
from erpnext.regional.india.utils import get_gst_accounts, get_place_of_supply

from erpnext.regional.india.e_invoice.utils import (GSPConnector,raise_document_name_too_long_error,read_json,
	validate_mandatory_fields,get_doc_details,get_return_doc_reference,
	get_eway_bill_details,validate_totals,show_link_to_error_log,santize_einvoice_fields,safe_json_load,get_payment_details,
	validate_eligibility,update_item_taxes,get_party_details,update_other_charges,
	get_overseas_address_details, validate_address_fields, sanitize_for_json, log_error)

def update_invoice_taxes(invoice, invoice_value_details):
	gst_accounts = get_gst_accounts(invoice.company)
	gst_accounts_list = [d for accounts in gst_accounts.values() for d in accounts if d]

	invoice_value_details.total_cgst_amt = 0
	invoice_value_details.total_sgst_amt = 0
	invoice_value_details.total_igst_amt = 0
	invoice_value_details.total_cess_amt = 0
	invoice_value_details.total_other_charges = 0
	considered_rows = []

	for t in invoice.taxes:
		tax_amount = t.base_tax_amount_after_discount_amount
		if t.account_head in gst_accounts_list:
			if t.account_head in gst_accounts.cess_account:
				# using after discount amt since item also uses after discount amt for cess calc
				invoice_value_details.total_cess_amt += abs(t.base_tax_amount_after_discount_amount)

			for tax_type in ['igst', 'cgst', 'sgst']:
				if t.account_head in gst_accounts[f'{tax_type}_account']:

					invoice_value_details[f'total_{tax_type}_amt'] += abs(tax_amount)
				update_other_charges(t, invoice_value_details, gst_accounts_list, invoice, considered_rows)
		#finbyz changes 
		else:
			export_reverse_charge_account = frappe.db.get_value("GST Account",{'company':invoice.company,"parent": "GST Settings"},'export_reverse_charge_account')
			if t.account_head == export_reverse_charge_account:
				invoice_value_details.base_total_other_taxes = t.base_tax_amount
				invoice_value_details.total_other_taxes = t.tax_amount

			else:
				invoice_value_details.total_other_charges += abs(t.base_tax_amount_after_discount_amount)
		#finbyz changes end
	return invoice_value_details

def get_invoice_value_details(invoice):
	invoice_value_details = frappe._dict(dict())
	invoice_value_details.base_total = abs(sum([i.taxable_value for i in invoice.get('items')]))
	invoice_value_details.invoice_discount_amt = 0

	invoice_value_details.round_off = invoice.base_rounding_adjustment
	invoice_value_details.base_grand_total = abs(invoice.base_rounded_total) or abs(invoice.base_grand_total)
	invoice_value_details.grand_total = abs(invoice.rounded_total) or abs(invoice.grand_total)

	invoice_value_details = update_invoice_taxes(invoice, invoice_value_details)
	#finbyz changes 
	invoice_value_details.base_grand_total -= flt(invoice_value_details.base_total_other_taxes)
	invoice_value_details.grand_total -= flt(invoice_value_details.total_other_taxes)
	#finbyz changes end

	return invoice_value_details

def get_transaction_details(invoice):
	supply_type = ''
	if invoice.gst_category == 'Registered Regular': supply_type = 'B2B'
	elif invoice.gst_category == 'SEZ': supply_type = 'SEZWOP'
	# elif invoice.gst_category == 'Overseas': supply_type = 'EXPWOP'
	elif invoice.gst_category == 'Overseas' and invoice.export_type == "Without Payment of Tax": supply_type = 'EXPWOP' # Finbyz Changes
	elif invoice.gst_category == 'Overseas' and invoice.export_type == "With Payment of Tax": supply_type = 'EXPWP' # Finbyz Changes
	elif invoice.gst_category == 'Deemed Export': supply_type = 'DEXP'

	if not supply_type:
		rr, sez, overseas, export = bold('Registered Regular'), bold('SEZ'), bold('Overseas'), bold('Deemed Export')
		frappe.throw(_('GST category should be one of {}, {}, {}, {}').format(rr, sez, overseas, export),
			title=_('Invalid Supply Type'))

	return frappe._dict(dict(
		tax_scheme='GST',
		supply_type=supply_type,
		reverse_charge=invoice.reverse_charge
	))


def make_einvoice(invoice):
	validate_mandatory_fields(invoice)

	schema = read_json('einv_template')

	transaction_details = get_transaction_details(invoice)
	item_list = get_item_list(invoice)
	doc_details = get_doc_details(invoice)
	invoice_value_details = get_invoice_value_details(invoice)
	seller_details = get_party_details(invoice.company_address)

	if invoice.gst_category == 'Overseas':
		buyer_details = get_overseas_address_details(invoice.customer_address)
	else:
		buyer_details = get_party_details(invoice.customer_address)
		place_of_supply = get_place_of_supply(invoice, invoice.doctype)
		if place_of_supply:
			place_of_supply = place_of_supply.split('-')[0]
		else:
			place_of_supply = sanitize_for_json(invoice.billing_address_gstin)[:2]
		buyer_details.update(dict(place_of_supply=place_of_supply))

	seller_details.update(dict(legal_name=invoice.company))
	buyer_details.update(dict(legal_name=invoice.customer_name or invoice.customer))

	shipping_details = payment_details = prev_doc_details = eway_bill_details = frappe._dict({})
	if invoice.shipping_address_name and invoice.customer_address != invoice.shipping_address_name:
		if invoice.gst_category == 'Overseas':
			shipping_details = get_overseas_address_details(invoice.shipping_address_name)
		else:
			shipping_details = get_party_details(invoice.shipping_address_name, skip_gstin_validation=True)

	# Finbyz Changes START: If Export Invoice then For Eway Bill generation Ship to Details Are Mandatory and Ship To Pincode and Ship to State Code Should be Pincode and State Code of Port/Place From India
	# In case of export transactions for goods, if e-way bill is required along with IRN, then the 'Ship-To' address should be of the place/port in India from where the goods are being exported. Otherwise E-way bill can be generated later based on IRN, by passing the 'Ship-To' address as the place/port address of India from where the goods are being exported .
	if invoice.get("eway_bill_ship_to_address") and invoice.gst_category == "Overseas":
		shipping_details = get_port_address_details(invoice.eway_bill_ship_to_address, skip_gstin_validation=True)
	# Finbyz Changes END

	dispatch_details = frappe._dict({})
	if invoice.dispatch_address_name:
		dispatch_details = get_party_details(invoice.dispatch_address_name, skip_gstin_validation=True)

	if invoice.is_pos and invoice.base_paid_amount:
		payment_details = get_payment_details(invoice)

	if invoice.is_return and invoice.return_against:
		prev_doc_details = get_return_doc_reference(invoice)

	if invoice.transporter and not invoice.is_return:
		eway_bill_details = get_eway_bill_details(invoice)

	# not yet implemented
	period_details = export_details = frappe._dict({})

	einvoice = schema.format(
		transaction_details=transaction_details, doc_details=doc_details, dispatch_details=dispatch_details,
		seller_details=seller_details, buyer_details=buyer_details, shipping_details=shipping_details,
		item_list=item_list, invoice_value_details=invoice_value_details, payment_details=payment_details,
		period_details=period_details, prev_doc_details=prev_doc_details,
		export_details=export_details, eway_bill_details=eway_bill_details
	)

	try:
		einvoice = safe_json_load(einvoice)
		einvoice = santize_einvoice_fields(einvoice)
	except Exception:
		show_link_to_error_log(invoice, einvoice)

	try:
		validate_totals(einvoice)
	except Exception:
		log_error(einvoice)
		raise

	return einvoice

def get_item_list(invoice):
	item_list = []

	for d in invoice.items:
		einvoice_item_schema = read_json('einv_item_template')
		item = frappe._dict({})
		item.update(d.as_dict())

		item.sr_no = d.idx
		item.description = json.dumps(d.item_name)[1:-1]

		# Finbyz changes Start: Wherever Quantity is calculating based on concentration with qty 
		try:
			item.qty = abs(item.quantity)
		except:
			item.qty = abs(item.qty)
		# Finbyz Changes End
		
		if invoice.apply_discount_on == 'Net Total' and invoice.discount_amount:
			item.discount_amount = abs(item.base_amount - item.base_net_amount)
		else:
			item.discount_amount = 0

		item.unit_rate = abs((abs(item.taxable_value) - item.discount_amount)/ item.qty)
		item.gross_amount = abs(item.taxable_value) + item.discount_amount
		item.taxable_value = abs(item.taxable_value)

		item.batch_expiry_date = frappe.db.get_value('Batch', d.batch_no, 'expiry_date') if d.batch_no else None
		item.batch_expiry_date = format_date(item.batch_expiry_date, 'dd/mm/yyyy') if item.batch_expiry_date else None
		#finbyz Changes
		if frappe.db.get_value('Item', d.item_code, 'is_stock_item') or frappe.db.get_value('Item', d.item_code, 'is_not_service_item'):
			item.is_service_item = 'N'  
		else:
			item.is_service_item = 'Y'
		#finbyz changes end
		
		item.serial_no = ""

		item = update_item_taxes(invoice, item)
		
		item.total_value = abs(
			item.taxable_value + item.igst_amount + item.sgst_amount +
			item.cgst_amount + item.cess_amount + item.cess_nadv_amount + item.other_charges
		)
		einv_item = einvoice_item_schema.format(item=item)
		item_list.append(einv_item)

	return ', '.join(item_list)

def get_port_address_details(address_name, skip_gstin_validation):
	addr = frappe.get_doc('Address', address_name)

	validate_address_fields(addr, skip_gstin_validation= skip_gstin_validation)

	return frappe._dict(dict(
		gstin='URP',
		legal_name=sanitize_for_json(addr.address_title),
		location=addr.city,
		address_line1=sanitize_for_json(addr.address_line1),
		address_line2=sanitize_for_json(addr.address_line2),
		pincode= addr.pincode, state_code= addr.gst_state_number
	))
