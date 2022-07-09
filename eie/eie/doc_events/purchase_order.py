import frappe

def validate(self,method):
	for row in self.items:
		row.cost_center = self.cost_center


def validate_items(self,method):
	data = frappe.get_list("Product Bundle", fields='new_item_code')
	item_list = [d.new_item_code for d in data]
	for row in self.items:
		if row.item_code in item_list:
			frappe.throw(f"Row {row.idx}:Product Bundle item Not allowed in Purchase Order")