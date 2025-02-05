import frappe

def validate(self,method):
	check_disable_warehouse(self, method)
	
def check_disable_warehouse(self, method):
    for row in self.items:
        warehouse = frappe.db.get_value("Warehouse", row.warehouse, "disabled")
        if warehouse == 1:
            frappe.throw(f"Selected Warehouse is Disabled in Row {row.idx}")