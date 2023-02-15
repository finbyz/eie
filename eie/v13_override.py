import frappe
from frappe.utils import cstr, flt
from six import iteritems
from frappe import _

def get_place_of_supply(party_details, doctype):
	if not frappe.get_meta('Address').has_field('gst_state'): return

	if doctype in ("Sales Invoice", "Delivery Note", "Sales Order", "Quotation"):
		address_name = party_details.shipping_address_name or party_details.customer_address # finbyz change
	elif doctype in ("Purchase Invoice", "Purchase Order", "Purchase Receipt"):
		address_name = party_details.shipping_address or party_details.supplier_address

	if address_name:
		address = frappe.db.get_value("Address", address_name, ["gst_state", "gst_state_number", "gstin"], as_dict=1)
		if address and address.gst_state and address.gst_state_number:
			party_details.gstin = address.gstin
			return cstr(address.gst_state_number) + "-" + cstr(address.gst_state)


def get_pending_raw_materials(self, backflush_based_on=None):
		"""
			issue (item quantity) that is pending to issue or desire to transfer,
			whichever is less
		"""
		item_dict = get_pro_order_required_items(self,backflush_based_on)

		max_qty = flt(self.pro_doc.qty)

		allow_overproduction = False
		overproduction_percentage = flt(frappe.db.get_single_value("Manufacturing Settings",
			"overproduction_percentage_for_work_order"))

		to_transfer_qty = flt(self.pro_doc.material_transferred_for_manufacturing) + flt(self.fg_completed_qty)
		transfer_limit_qty = max_qty + ((max_qty * overproduction_percentage) / 100)

		if transfer_limit_qty >= to_transfer_qty:
			allow_overproduction = True

		for item, item_details in iteritems(item_dict):
			pending_to_issue = flt(item_details.required_qty) - flt(item_details.transferred_qty)
			desire_to_transfer = flt(self.fg_completed_qty) * flt(item_details.required_qty) / max_qty

			if (desire_to_transfer <= pending_to_issue or allow_overproduction): # finbyz change remove backflush condition
				item_dict[item]["qty"] = desire_to_transfer
			elif pending_to_issue > 0:
				item_dict[item]["qty"] = pending_to_issue
			else:
				item_dict[item]["qty"] = 0

		# delete items with 0 qty
		for item in item_dict.keys():
			if not item_dict[item]["qty"]:
				del item_dict[item]

		# show some message
		if not len(item_dict):
			frappe.msgprint(_("""All items have already been transferred for this Work Order."""))

		return item_dict

def get_pro_order_required_items(self, backflush_based_on=None):
		item_dict = frappe._dict()
		pro_order = frappe.get_doc("Work Order", self.work_order)
		if not frappe.db.get_value("Warehouse", pro_order.wip_warehouse, "is_group"):
			wip_warehouse = pro_order.wip_warehouse
		else:
			wip_warehouse = None

		for d in pro_order.get("required_items"):
			if ( ((flt(d.required_qty) > flt(d.transferred_qty))) and # finbyz chnage remove condition
				(d.include_item_in_manufacturing or self.purpose != "Material Transfer for Manufacture")):
				item_row = d.as_dict()
				if d.source_warehouse and not frappe.db.get_value("Warehouse", d.source_warehouse, "is_group"):
					item_row["from_warehouse"] = d.source_warehouse

				item_row["to_warehouse"] = wip_warehouse
				if item_row["allow_alternative_item"]:
					item_row["allow_alternative_item"] = pro_order.allow_alternative_item

				item_dict.setdefault(d.item_code, item_row)

		return item_dict