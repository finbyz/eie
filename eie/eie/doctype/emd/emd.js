// Copyright (c) 2018, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('EMD', {
	refresh: function(frm) {
		frm.set_query('customer', function(doc) {
			return {
				filters: {
					"disabled": 0,
				}
			};
		});

		if (frm.doc.return_journal_entry) {
			cur_frm.set_df_property("return_account", "read_only", 1);
			cur_frm.set_df_property("interest_amount", "read_only", 1);
			cur_frm.set_df_property("interest_account", "read_only", 1);
			cur_frm.set_df_property("return_date", "read_only", 1);
		}
		else {
			cur_frm.set_df_property("return_account", "read_only", 0);
			cur_frm.set_df_property("interest_amount", "read_only", 0);
			cur_frm.set_df_property("interest_account", "read_only", 0);
			cur_frm.set_df_property("return_date", "read_only", 0);
		}
	}
});
