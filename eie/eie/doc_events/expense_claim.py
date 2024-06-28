from frappe import _

def before_validate(self, method):
    update_cost_centre_in_expenses(self)

def update_cost_centre_in_expenses(self):
    for item in self.expenses:
        item.cost_center = self.cost_center