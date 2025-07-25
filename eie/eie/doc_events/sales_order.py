import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.model.utils import get_fetch_values
from erpnext.stock.doctype.item.item import get_item_defaults
from frappe.contacts.doctype.address.address import get_company_address
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from frappe.utils import cstr, flt, getdate, cint, nowdate, add_days, get_link_to_form, strip_html

def validate(self, method):
    if self.customer:
            # Define party_type and party variables
            # Define party_type and party variables
        party_type = "Customer"
        party = self.customer
        
        # Query to get company-wise outstanding amounts
        company_wise_total_unpaid = frappe.db.sql(
            """
            SELECT company, (sum(debit_in_account_currency) - sum(credit_in_account_currency)) as outstanding
            FROM `tabGL Entry`
            WHERE party_type = %s 
            AND party = %s
            AND is_cancelled = 0
            GROUP BY company
            """,
            (party_type, party),
            as_dict=True
        )
        
        self.customer_outstanding = company_wise_total_unpaid[0].outstanding if company_wise_total_unpaid else 0
    customer_group  = frappe.db.get_value("Customer",self.customer,"customer_group")
    if customer_group:
        # Get all customers in the same customer group
        customers_in_group = frappe.db.sql(
            """
            SELECT name 
            FROM `tabCustomer` 
            WHERE customer_group = %s
            """,
            (customer_group,),
            as_dict=True
        )
        
        if customers_in_group:
            # Create a tuple of customer names for the IN clause
            customer_names = tuple([customer.name for customer in customers_in_group])
            
            # Query to get total outstanding for all customers in the group
            customer_group_outstanding = frappe.db.sql(
                """
                SELECT company, (sum(debit_in_account_currency) - sum(credit_in_account_currency)) as outstanding
                FROM `tabGL Entry`
                WHERE party_type = 'Customer' 
                AND party IN %s
                GROUP BY company
                """,
                (customer_names,),
                as_dict=True
            )
            self.customer_group_outstanding = customer_group_outstanding[0].outstanding if customer_group_outstanding else 0
        else:
            self.customer_group_outstanding = 0
    else:
        self.customer_group_outstanding = 0
    # validate_cost_center(self, method)
    # for row in self.items:
    #     row.cost_center = self.cost_center

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, kwargs=None):
    from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
    from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
        get_sre_details_for_voucher,
        get_sre_reserved_qty_details_for_voucher,
        get_ssb_bundle_for_voucher,
    )

    if not kwargs:
        kwargs = {
            "for_reserved_stock": frappe.flags.args and frappe.flags.args.for_reserved_stock,
            "skip_item_mapping": frappe.flags.args and frappe.flags.args.skip_item_mapping,
        }

    kwargs = frappe._dict(kwargs)

    sre_details = {}
    if kwargs.for_reserved_stock:
        sre_details = get_sre_reserved_qty_details_for_voucher("Sales Order", source_name)

    mapper = {
        "Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
        "Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
        "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
    }

    def set_missing_values(source, target):
        target.run_method("set_missing_values")
        target.run_method("set_po_nos")
        target.run_method("calculate_taxes_and_totals")
        target.run_method("set_use_serial_batch_fields")

        if source.company_address:
            target.update({"company_address": source.company_address})
        else:
            # set company address
            target.update(get_company_address(target.company))

        if target.company_address:
            target.update(get_fetch_values("Delivery Note", "company_address", target.company_address))

        # if invoked in bulk creation, validations are ignored and thus this method is nerver invoked
        if frappe.flags.bulk_transaction:
            # set target items names to ensure proper linking with packed_items
            target.set_new_name()

        make_packing_list(target)

    def condition(doc):
        if doc.name in sre_details:
            del sre_details[doc.name]
            return False

        # make_mapped_doc sets js `args` into `frappe.flags.args`
        if frappe.flags.args and frappe.flags.args.delivery_dates:
            if cstr(doc.delivery_date) not in frappe.flags.args.delivery_dates:
                return False

        return abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier != 1

    def update_item(source, target, source_parent):
        target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
        target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
        target.qty = flt(source.qty) - flt(source.delivered_qty)

        item = get_item_defaults(target.item_code, source_parent.company)
        item_group = get_item_group_defaults(target.item_code, source_parent.company)

        if item:
            target.cost_center = source.cost_center

    if not kwargs.skip_item_mapping:
        mapper["Sales Order Item"] = {
            "doctype": "Delivery Note Item",
            "field_map": {
                "rate": "rate",
                "name": "so_detail",
                "parent": "against_sales_order",
            },
            "condition": condition,
            "postprocess": update_item,
        }

    so = frappe.get_doc("Sales Order", source_name)
    target_doc = get_mapped_doc("Sales Order", so.name, mapper, target_doc)

    if not kwargs.skip_item_mapping and kwargs.for_reserved_stock:
        sre_list = get_sre_details_for_voucher("Sales Order", source_name)

        if sre_list:

            def update_dn_item(source, target, source_parent):
                update_item(source, target, so)

            so_items = {d.name: d for d in so.items if d.stock_reserved_qty}

            for sre in sre_list:
                if not condition(so_items[sre.voucher_detail_no]):
                    continue

                dn_item = get_mapped_doc(
                    "Sales Order Item",
                    sre.voucher_detail_no,
                    {
                        "Sales Order Item": {
                            "doctype": "Delivery Note Item",
                            "field_map": {
                                "rate": "rate",
                                "name": "so_detail",
                                "parent": "against_sales_order",
                            },
                            "postprocess": update_dn_item,
                        }
                    },
                    ignore_permissions=True,
                )

                dn_item.qty = flt(sre.reserved_qty) * flt(dn_item.get("conversion_factor", 1))

                if sre.reservation_based_on == "Serial and Batch" and (sre.has_serial_no or sre.has_batch_no):
                    dn_item.serial_and_batch_bundle = get_ssb_bundle_for_voucher(sre)

                target_doc.append("items", dn_item)
            else:
                # Correct rows index.
                for idx, item in enumerate(target_doc.items):
                    item.idx = idx + 1

    # Should be called after mapping items.
    set_missing_values(so, target_doc)

    return target_doc

def validate_cost_center(self, method):
    cost_center = self.cost_center
    cc = frappe.db.get_value("Cost Center", cost_center, "disabled")
    if cc == 1:
        frappe.throw("Cost Center is Disabled.")



# @frappe.whitelist()
# def highlight_sales_order_items(sales_order_name):
#     stock_entry_item_codes = frappe.db.get_all(
#         'Stock Entry Detail',
#         fields=['item_code'],
#         filters={'parentfield': 'items', 'parent': ['in', frappe.db.get_all(
#             'Stock Entry',
#             filters={'sales_order': sales_order_name},
#             pluck='name'
#         )]},
        
#         pluck='item_code'
#     )

#     sales_order = frappe.get_doc('Sales Order', sales_order_name)
#     highlighted_rows = []

#     for item in sales_order.items:
#         if item.item_code in stock_entry_item_codes:
#             # frappe.msgprint(item.item_code)
#             highlighted_rows.append(item.idx)  

#     return highlighted_rows


# @frappe.whitelist()
# def highlight_sales_order_packed_items(sales_order_name):
#     stock_entry_item_codes = frappe.db.get_all(
#         'Stock Entry Detail',
#         fields=['item_name'],
#         filters={'parentfield': 'items', 'parent': ['in', frappe.db.get_all(
#             'Stock Entry',
#             filters={'sales_order': sales_order_name},
#             pluck='name'
#         )]},
        
#         pluck='item_name'
#     )

#     sales_order = frappe.get_doc('Sales Order', sales_order_name)
#     highlighted_rows = []

#     for item in sales_order.packed_items:
#         if item.item_name in stock_entry_item_codes:
#             highlighted_rows.append(item.idx)  

#     return highlighted_rows

@frappe.whitelist()
def highlight_sales_order_items(sales_order_name):
    # Get item codes from Stock Entries with docstatus = 1
    stock_entry_item_codes = frappe.db.get_all(
        'Stock Entry Detail',
        fields=['item_code'],
        filters={
            'parentfield': 'items',
            'parent': ['in', frappe.db.get_all(
                'Stock Entry',
                filters={'sales_order': sales_order_name, 'docstatus': 1},  # Only submitted stock entries
                pluck='name'
            )]
        },
        pluck='item_code'
    )

    sales_order = frappe.get_doc('Sales Order', sales_order_name)
    highlighted_rows = []

    for item in sales_order.items:
        if item.item_code in stock_entry_item_codes:
            highlighted_rows.append(item.idx)  # Add the row index to highlight

    return highlighted_rows


@frappe.whitelist()
def highlight_sales_order_packed_items(sales_order_name):
    # Get item names from Stock Entries with docstatus = 1
    stock_entry_item_codes = frappe.db.get_all(
        'Stock Entry Detail',
        fields=['item_name'],
        filters={
            'parentfield': 'items',
            'parent': ['in', frappe.db.get_all(
                'Stock Entry',
                filters={'sales_order': sales_order_name, 'docstatus': 1},  # Only submitted stock entries
                pluck='name'
            )]
        },
        pluck='item_name'
    )

    sales_order = frappe.get_doc('Sales Order', sales_order_name)
    highlighted_rows = []

    for item in sales_order.packed_items:
        if item.item_name in stock_entry_item_codes:
            highlighted_rows.append(item.idx)  # Add the row index to highlight

    return highlighted_rows

# 

@frappe.whitelist()
def update_packed_qty_from_stock_entry(stock_entry_name):
    # Fetch the Stock Entry document
    stock_entry = frappe.get_doc('Stock Entry', stock_entry_name)
    
    # Ensure the Stock Entry has a Sales Order field
    if not hasattr(stock_entry, 'sales_order') or not stock_entry.sales_order:
        return {"status": "error", "message": "Sales Order not found in Stock Entry"}

    # Iterate through items in Stock Entry
    for stock_item in stock_entry.items:
        # Use the parent 'sales_order' field
        sales_order = stock_entry.sales_order
        
        # Fetch matching Sales Order Items
        sales_order_items = frappe.get_all(
            'Sales Order Item',
            filters={
                'parent': sales_order,
                'item_code': stock_item.item_code,
            },
            fields=['name', 'packed_qty']
        )

        for so_item in sales_order_items:
            
            # Update Packed Qty
            new_packed_qty = (so_item.packed_qty or 0) + stock_item.qty
            # new_packed_qty = 0
            frappe.db.set_value('Sales Order Item', so_item.name, 'packed_qty', new_packed_qty)

@frappe.whitelist()
def update_packed_qty_from_stock_entry_packed_items(stock_entry_name):
    # Fetch the Stock Entry document
    stock_entry = frappe.get_doc('Stock Entry', stock_entry_name)
    
    # Ensure the Stock Entry has a Sales Order field
    if not hasattr(stock_entry, 'sales_order') or not stock_entry.sales_order:
        return {"status": "error", "message": "Sales Order not found in Stock Entry"}

    # Iterate through items in Stock Entry
    for stock_item in stock_entry.items:
        # Use the parent 'sales_order' field
        sales_order = stock_entry.sales_order
        
        # Fetch matching Sales Order Items
        sales_order_items = frappe.get_all(
            'Packed Item',
            filters={
                'parent': sales_order,
                'item_code': stock_item.item_code,
            },
            fields=['name', 'qty_packed']
        )

        for so_item in sales_order_items:
            # Update Packed Qty
            new_packed_qty = (so_item.qty_packed or 0) + stock_item.qty
            frappe.db.set_value('Packed Item', so_item.name, 'qty_packed', new_packed_qty)