
import frappe

@frappe.whitelist()
def get_sales_invoice_items(sales_invoice_list):
    sales_invoice_list = frappe.parse_json(sales_invoice_list)
    
    items = []
    
    for invoice in sales_invoice_list:
        invoice_name = invoice.get('sales_invoice') 
        
        if invoice_name:
            invoice_doc = frappe.get_doc('Sales Invoice', invoice_name)
            
            for item in invoice_doc.items:
                service_engineers = frappe.db.get_values("Service Engineer Table", {"parent": item.item_code}, "service_engineer")
                service_engineers = [i[0] for i in service_engineers]
                items.append({
                    'item_code': item.item_code,
                    'qty': item.qty,
                    'sales_invoice_no': invoice_doc.name,
                    'date': invoice_doc.posting_date,
                    "service_engineers": service_engineers
                })
    
    return items


import frappe

@frappe.whitelist()
def get_service_engineers(item_code):
    """Return list of service engineers for the given Item"""

    if not item_code:
        return []
    
    item = frappe.get_doc("Item", item_code)

    if hasattr(item, "service_engineer"):
        return [row.service_engineer for row in item.service_engineer]
    
    return []
