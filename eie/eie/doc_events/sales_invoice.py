import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cstr, flt, getdate, cint, nowdate, add_days, get_link_to_form, strip_html
def validate(self,method):
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
                AND is_cancelled = 0
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
    for row in self.items:
        row.cost_center = self.cost_center

# @frappe.whitelist()
# def make_delivery_note(source_name, target_doc=None):
# 	def set_missing_values(source, target):
# 		target.ignore_pricing_rule = 1
# 		target.run_method("set_missing_values")
# 		target.run_method("set_po_nos")
# 		target.run_method("calculate_taxes_and_totals")

# 	def update_item(source_doc, target_doc, source_parent):
# 		target_doc.qty = flt(source_doc.qty) - flt(source_doc.delivered_qty)
# 		target_doc.stock_qty = target_doc.qty * flt(source_doc.conversion_factor)

# 		target_doc.base_amount = target_doc.qty * flt(source_doc.base_rate)
# 		target_doc.amount = target_doc.qty * flt(source_doc.rate)

# 	doclist = get_mapped_doc("Sales Invoice", source_name, 	{
# 		"Sales Invoice": {
# 			"doctype": "Delivery Note",
#             "field_map": {
# 				"cost_center":"cost_center"
# 			},
# 			"validation": {
# 				"docstatus": ["=", 1]
# 			}
# 		},
# 		"Sales Invoice Item": {
# 			"doctype": "Delivery Note Item",
# 			"field_map": {
# 				"name": "si_detail",
# 				"parent": "against_sales_invoice",
# 				"serial_no": "serial_no",
# 				"sales_order": "against_sales_order",
# 				"so_detail": "so_detail",
# 				"cost_center": "cost_center"
# 			},
# 			"postprocess": update_item,
# 			"condition": lambda doc: doc.delivered_by_supplier!=1
# 		},
# 		"Sales Taxes and Charges": {
# 			"doctype": "Sales Taxes and Charges",
# 			"add_if_empty": True
# 		},
# 		"Sales Team": {
# 			"doctype": "Sales Team",
# 			"field_map": {
# 				"incentives": "incentives"
# 			},
# 			"add_if_empty": True
# 		}
# 	}, target_doc, set_missing_values)
# 	return doclist