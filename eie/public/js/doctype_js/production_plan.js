frappe.ui.form.on("Production Plan", {
    get_items_for_mr___(frm) {
		frm.events.get_items_for_material_requests(frm, [
			{
				warehouse: frm.doc.for_warehouse,
			},
		]);
	},
    get_items_for_material_requests(frm, warehouses) {
		frappe.call({
			method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_items_for_material_requests",
			freeze: true,
			args: {
				doc: frm.doc,
				warehouses: warehouses || [],
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value("mr_items", []);
					r.message.forEach((row) => {
						let d = frm.add_child("mr_items");
						for (let field in row) {
							if (field !== "name") {
								d[field] = row[field];
							}
						}
					});
				}
				refresh_field("mr_items");
			},
		});
	},
});