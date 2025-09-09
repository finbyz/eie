

import frappe
from frappe.model.document import Document

class ChargeableComplaintEntry(Document):
    
    @frappe.whitelist()
    def get_items_from_sales_invoices(self):
        """Get items from all sales invoices in the child table"""
        
        sales_invoices = []
        for row in self.get("sales_invoices"):
            if row.sales_invoice:
                sales_invoices.append(row.sales_invoice)
        
        if not sales_invoices:
            frappe.msgprint("No sales invoices found in the table")
            return []
        
        
        self.set("items", [])
    
        items_added = 0
        
        
        for invoice_name in sales_invoices:
            try:
                sales_invoice = frappe.get_doc("Sales Invoice", invoice_name)
                
                for item in sales_invoice.items:
                    item_row = self.append("items", {})
                    item_row.item_code = item.item_code
                    item_row.item_name = item.item_name
                    item_row.qty = item.qty
                    item_row.uom = item.uom
                    item_row.description = item.description
                    item_row.sales_invoice = invoice_name  # Track source invoice
                    item_row.sales_invoice_date = sales_invoice.posting_date  # Add posting date
                    
                    items_added += 1
                    
            except frappe.DoesNotExistError:
                frappe.msgprint(f"Sales Invoice {invoice_name} does not exist")
                continue
            except frappe.PermissionError:
                frappe.msgprint(f"No permission to access Sales Invoice {invoice_name}")
                continue
            except Exception as e:
                frappe.log_error(f"Error processing Sales Invoice {invoice_name}: {str(e)}")
                continue
        
        if items_added > 0:
            self.save()
            frappe.msgprint(f"{items_added} items have been added from selected Sales Invoices")
        else:
            frappe.msgprint("No items were added. Please check if the Sales Invoices have items.")
        
        return items_added