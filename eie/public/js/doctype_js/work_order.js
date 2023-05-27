frappe.ui.form.on("Work Order", {
    setup: function(frm) {
        frm.set_query("bom_no", function() {
			if (frm.doc.production_item) {
				return {
					query: "erpnext.controllers.queries.bom",
					filters: {item: cstr(frm.doc.production_item) , company : frm.doc.company}
				};
			} else {
				frappe.msgprint(__("Please enter Production Item first"));
			}
		});
    }
})