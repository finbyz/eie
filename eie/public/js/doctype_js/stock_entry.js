
this.frm.fields_dict.sales_order.get_query = function(doc){
	return {
		"filters": {
			'docstatus': 1,
            'company': doc.company
           // 'status': ["!=",["Close","Completed"]]
		}
	};
}
frappe.ui.form.on("Stock Entry", {
    get_items_from_so:function(frm){
        frappe.call({
			method: "eie.eie.doc_events.stock_entry.insert_se_items",
			args: {
				sales_order : frm.doc.sales_order,
			},
			callback: function (r) {
                console.log(r.message)
                frm.doc.items=[]
				r.message.forEach(function (d) {
                    if (d.qty != 0){
                    let a = frappe.model.add_child(frm.doc,"Stock Entry Detail","items");
                    frappe.model.set_value(a.doctype, a.name, 'item_code',d.item_code);
                    frappe.model.set_value(a.doctype, a.name, 'item_name',d.item_name);
                    frappe.model.set_value(a.doctype, a.name, 'qty',d.qty);
                    frappe.model.set_value(a.doctype, a.name, 'uom',d.uom);
                    frappe.model.set_value(a.doctype, a.name, 's_warehouse',d.s_warehouse);
                    }
                });
			}
		});
    }})
// frappe.ui.form.on("Stock Entry", {
//     get_items_from_so: function(frm){
//         frm.doc.items = []
//         frappe.model.with_doc("Sales Order", frm.doc.sales_order, function() {
//             let so_doc= frappe.model.get_doc("Sales Order", frm.doc.sales_order)
//             frm.set_value("from_warehouse",so_doc.set_warehouse)
//             so_doc.items.forEach(function(row){
//                     let d = frappe.model.add_child(frm.doc,"Stock Entry Detail","items");
//                     frappe.model.set_value(d.doctype, d.name, 'item_code', row.item_code);
//                     frappe.model.set_value(d.doctype, d.name, 'item_name', row.item_name);
//                     frappe.model.set_value(d.doctype, d.name, 'qty', row.qty);
//                     frappe.model.set_value(d.doctype, d.name, 'uom', row.uom);
//                     frappe.model.set_value(d.doctype, d.name, 's_warehouse', row.warehouse);    
//                 });
//         })
//         frappe.model.with_doc("Sales Order", frm.doc.sales_order, function() {
//             let so_doc= frappe.model.get_doc("Sales Order", frm.doc.sales_order)    
//             so_doc.packed_items.forEach(function(row){
//                     let d = frappe.model.add_child(frm.doc,"Stock Entry Detail","items");
//                     frappe.model.set_value(d.doctype, d.name, 'item_code', row.item_code);
//                     frappe.model.set_value(d.doctype, d.name, 'item_name', row.item_name);
//                     frappe.model.set_value(d.doctype, d.name, 'qty', row.qty);
//                     frappe.model.set_value(d.doctype, d.name, 'uom', row.uom);
//                     frappe.model.set_value(d.doctype, d.name, 's_warehouse', row.warehouse);    
//                 });
//         })
//     }
// })