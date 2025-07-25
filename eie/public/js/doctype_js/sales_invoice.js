frappe.ui.form.on("Sales Invoice", {
	refresh: function(frm){
        cur_frm.set_query("item_code", "items", function(doc) {
			if(doc.company == "EIE Instruments Pvt. Ltd."){
				return{
					query: "eie.api.new_item_query",
					filters:{'dont_allow_sales_in_eie':0,'is_sales_item': 1}
				}
			}
			else{
				return {
					query: "eie.api.new_item_query",
					filters: {'is_sales_item': 1}
				}
			}
			
		});
        cur_frm.set_query("bank_account", "bank_accounts", function(doc) {
			return {
				filters: {
					"company": doc.company
				}
			}
		});
    },
    cost_center:function(frm){
        if(frm.doc.cost_center){
            frm.doc.items.forEach(d => {
                frappe.model.set_value(d.doctype, d.name, 'cost_center', frm.doc.cost_center);
            });
        }
    },
    transporter: function(frm){
        if (!frm.doc.transporter){
            frm.set_value("transporter_name",null);
            frm.set_value("gst_transporter_id",null);
        }
    }
});

frappe.ui.form.on('Sales Invoice', {
    get_email_recipients: function(frm, field) {
        if (field === 'cc') {
            const raw = frm.doc.other_emails || "";
            const emails = raw
                .split(",")
                .map(e => e.trim())
                .filter(e => validate_email(e));
            return emails;
        }
    }
});

// Helper
function validate_email(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}
