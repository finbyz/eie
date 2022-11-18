import frappe

def validate(self, method):
    if not self.industry:
        frappe.throw("Industry is Mandatory.")