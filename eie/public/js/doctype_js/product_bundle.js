// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Product Bundle", {
	refresh: function (frm) {
		frm.toggle_enable("new_item_code", frm.is_new());
		frm.set_query("new_item_code", () => {
			return {
				query: "erpnext.selling.doctype.product_bundle.product_bundle.get_new_item_code",
			};
		});

		frm.set_query("item_code", "items", () => {
			return {
				filters: {
					has_variants: 0,
				},
			};
		});
		frm.add_custom_button('Update Prices', function() {
            frappe.call({
                method: 'eie.api.update_product_bundle_prices',
                args: {
                    docname: frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc) {
                        frm.reload_doc(); 
                    }
                }
            });
        });
	},
});
