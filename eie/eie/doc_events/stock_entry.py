import frappe

@frappe.whitelist()
def insert_se_items(sales_order):
    so_name = sales_order
    so_items = frappe.db.sql(f""" SELECT * from `tabSales Order Item` Where parent =  "{so_name}" order by idx asc""",as_dict = True)
    so_packed_items = frappe.db.sql(f""" SELECT * from `tabPacked Item` Where parent =  "{so_name}" order by idx asc """,as_dict = True)
    so = so_items + so_packed_items
    
    data = frappe.db.sql(f"""
            select sed.item_code , sed.item_name , sum(sed.qty) as qty , sed.uom , sed.s_warehouse
            from `tabStock Entry` as se
            LEFT JOIN `tabStock Entry Detail` as sed on sed.parent = se.name 
            WHERE se.sales_order = '{so_name}' and se.docstatus = 1 and se.stock_entry_type = 'Material Transfer'
            Group By sed.item_code
        """,as_dict=1)
    
    sed = {}
    
    for row in data:
        sed[row.item_code] = row
        
    se_items =[]
    for row in so:
        items = {}
        if sed.get(row.item_code):
            if row.item_code == sed[row.item_code].item_code:
                quantity = row.qty - sed[row.item_code].qty
                if quantity != 0:
                    items.update({"item_code":row.item_code , "item_name" : row.item_name , 'qty':quantity , 'uom':row.uom , 's_warehouse' :row.get('warehouse')})
                    se_items.append(items)
        else:
            items.update({"item_code":row.item_code , "item_name" : row.item_name , 'qty':row.qty , 'uom':row.uom , 's_warehouse' :row.get('warehouse')})
            se_items.append(items)
                         
    return se_items
