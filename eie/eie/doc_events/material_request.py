import frappe

def check_item(doc, handler):
    existing_rows = {}
    rows_to_remove = []

    for i, item in enumerate(doc.items):
        # Create a unique identifier for the row using item_code and warehouse
        key = (item.item_code, item.warehouse)

        # Check if the key already exists in existing_rows
        if key in existing_rows:
            # If it does, mark the row for removal
            rows_to_remove.append(i)
        else:
            # If it doesn't, add it to existing_rows
            existing_rows[key] = i

    # Remove duplicate rows
    for i in reversed(rows_to_remove):
        doc.items.pop(i)