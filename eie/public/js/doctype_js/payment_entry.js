
{% include "eie/public/js/sms_manager.js" %}

frappe.ui.form.on('Payment Entry', {
    refresh: (frm) => {
        console.log('sms sending finbyz')
		
		if(cur_frm.doc.docstatus===1 && !in_list(["Lost", "Stopped", "Closed"], cur_frm.doc.status)){
			cur_frm.page.add_menu_item(__('Send SMS'), function() { frm.trigger('send_sms') });
		}
    },
    send_sms: function(frm) {
		var sms_man = new erpnext.SMSManager(frm.doc);
	}, 
})