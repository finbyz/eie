import frappe

def validate(self,method):
    for row in self.items:
        row.cost_center = self.cost_center

def on_submit(self , method):
    company_doc = frappe.get_doc('Company' , self.company)
    if company_doc.make_mandatory_warehouse_for_delivery_note:
        for row in self.items:
            if row.warehouse != company_doc.warehouse:
                frappe.throw("Warehouse <b>{}</b> is mandatory for the Delivery Note".format(company_doc.warehouse))
        for row in self.packed_items:
            if row.warehouse != company_doc.warehouse:
                frappe.throw("Warehouse <b>{}</b> is mandatory for the Delivery Note".format(company_doc.warehouse))