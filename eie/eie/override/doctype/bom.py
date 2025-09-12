import frappe
from erpnext.manufacturing.doctype.bom.bom import BOM as _BOM


class BOM(_BOM):
    def calculate_cost(self, save_updates=False, update_hour_rate=False):
        """Custom BOM cost calculation"""

        # Call existing sub-methods
        self.calculate_op_cost(update_hour_rate)
        self.calculate_rm_cost(save=save_updates)
        self.calculate_sm_cost(save=save_updates)

        if save_updates:
            # not via doc event, table is not regenerated and needs updation
            self.calculate_exploded_cost()

        old_cost = self.total_cost

        self.total_cost = self.operating_cost + self.raw_material_cost - self.scrap_material_cost
        self.base_total_cost = (
            self.base_operating_cost + self.base_raw_material_cost - self.base_scrap_material_cost
        )
        self.grand_total_cost = self.total_operational_cost + self.raw_material_cost

        # Example: Add your custom adjustment
        self.total_cost += 100   # (You can replace with your logic)

        if self.total_cost != old_cost:
            self.flags.cost_updated = True

