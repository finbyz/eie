
from frappe.model.naming import make_autoname
import frappe

def validate(self,method):
	make_item_code(self ,method)

def make_item_code(self ,method):
	if not self.item_group_code:
		code_1,code_2,code_3,code_4,code_5="","","","",""
		if self.item_group:
			group1 = frappe.get_doc("Item Group", self.item_group , 'parent_item_group')
			if group1.code:
				code_1 = group1.code
			if group1.parent_item_group:
				group2 = frappe.get_doc("Item Group", group1.parent_item_group , 'parent_item_group')
				if group2.code:
					code_2 = group2.code
				if group2.parent_item_group:
					group3 = frappe.get_doc("Item Group", group2.parent_item_group , 'parent_item_group')
					if group3.code:
						code_3 = group3.code
					if group3.parent_item_group:
						group4 = frappe.get_doc("Item Group", group3.parent_item_group , 'parent_item_group')
						if group4.code:
							code_4 = group4.code
						if group4.parent_item_group:
							group5 = frappe.get_doc("Item Group", group3.parent_item_group , 'parent_item_group')
							if group5.code:
								code_5 = group5.code
		if code_1 and code_1 != None and code_1 != "":
			self.item_group_code = make_autoname('{}{}{}{}{}{}'.format(code_5 or "" , code_4 or "",code_3 or "",code_2 or "" , code_1 ,".#####"))