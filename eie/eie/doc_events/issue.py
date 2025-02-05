
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
                items.append({
                    'item_code': item.item_code,
                    'qty': item.qty,
                    'sales_invoice_no': invoice_doc.name,
                    'date': invoice_doc.posting_date
                })
    
    return items
