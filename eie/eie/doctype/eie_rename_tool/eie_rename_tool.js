// Copyright (c) 2018, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('EIE Rename Tool', {
	onload: function(frm) {
		return frappe.call({
			method: "eie.eie.doctype.eie_rename_tool.eie_rename_tool.get_doctypes",
			callback: function(r) {
				frm.set_df_property("select_doctype", "options", r.message);
			}
		});
	},
	refresh: function(frm) {
		frm.disable_save();
		if (!frm.doc.file_to_rename) {
			frm.get_field("rename_log").$wrapper.html("");
		}
		frm.page.set_primary_action(__("Rename"), function() {
			frm.get_field("rename_log").$wrapper.html("<p>Renaming...</p>");
			frappe.call({
				method: "eie.eie.doctype.eie_rename_tool.eie_rename_tool.upload",
				args: {
					select_doctype: frm.doc.select_doctype
				},
				callback: function(r) {
					frm.get_field("rename_log").$wrapper.html(r.message.join("<br>"));
				}
			});
		});
	}
});
