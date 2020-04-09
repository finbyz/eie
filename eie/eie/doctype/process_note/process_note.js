// Copyright (c) 2020, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Process Note', {
	// refresh: function(frm) {

	// }
	onload: function(frm){
		if(frm.doc.__islocal){
			frappe.db.get_value("Employee",{'user_id':frappe.session.user},'name',function(r){
				frm.set_value("created_by",r.name);
			})
		}
	}
});
