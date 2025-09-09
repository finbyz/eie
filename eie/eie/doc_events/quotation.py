import frappe

def validate(self, method):
    check_disable_warehouse(self,method)


def check_disable_warehouse(self, method):
    for row in self.items:
        warehouse = frappe.db.get_value("Warehouse", row.warehouse, "disabled")
        if warehouse == 1:
            frappe.throw(f"Selected Warehouse is Disabled in Row {row.idx}")



        
def check_disabled_item(self,method):
    # Map item_code → list of row numbers
    item_code_to_rows = {}
    for row in self.items:
        if row.item_code:
            item_code_to_rows.setdefault(row.item_code, []).append(row.idx)

    item_codes = list(item_code_to_rows.keys())

    if not item_codes:
        return  # No items to check

    # Fetch all disabled items from the Item master in one query
    disabled_item_codes = frappe.get_all(
        "Item",
        filters={
            "name": ["in", item_codes],
            "disabled": 1
        },
        pluck="name"
    )

    if disabled_item_codes:
        # Prepare the detailed error message
        details = [
            f"{code} (Rows {', '.join(map(str, item_code_to_rows[code]))})"
            for code in disabled_item_codes
        ]

        frappe.throw(
            "The following items are disabled and cannot be used:<br>{}".format(
                "<br>".join(details)
            )
        )




