import frappe
from frappe.utils import nowdate

def validate(self,method):
	validate_cost_center(self, method)
	for row in self.items:
		row.cost_center = self.cost_center


def validate_items(self,method):
	data = frappe.get_list("Product Bundle", fields='new_item_code')
	item_list = [d.new_item_code for d in data]
	for row in self.items:
		if row.item_code in item_list:
			frappe.throw(f"Row {row.idx}:Product Bundle item Not allowed in Purchase Order")

def validate_cost_center(self, method):
	cost_center = self.cost_center
	cc = frappe.db.get_value("Cost Center", cost_center, "disabled")
	if cc == 1:
		frappe.throw("Cost Center is Disabled.")


def auto_close_expired_pos():
    expired_pos = frappe.get_all("Purchase Order", 
        filters={
            "docstatus": 1,  # Submitted
            "status": ["not in", ["Closed", "Completed"]],
			"expiry_date":["is", "set"],
            "expiry_date": ["<", nowdate()],
            
        },
        fields=["name"]
    )
	
    for po in expired_pos:
        try:
            doc = frappe.get_doc("Purchase Order", po.name)
            doc.db_set("status", "Closed")
            frappe.db.commit()
            frappe.logger().info(f"Auto-closed PO: {po.name}")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Failed to auto-close PO {po.name}")
