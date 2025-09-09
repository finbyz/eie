frappe.ui.form.on('Journal Entry', {
    refresh(frm) {
        // your code here
    },
    party: function(frm) {
        console.log("from code side");
        if (frm.doc.link_to === "Supplier" && frm.doc.party) {
            frappe.db.get_value("Supplier", frm.doc.party, "pan")
                .then(r => {
                    if (r && r.message) {
                        frm.set_value("pan_no", r.message.pan);
                    }
                });
        }
        if (frm.doc.link_to === "Customer" && frm.doc.party) {
            frappe.db.get_value("Customer", frm.doc.party, "pan")
                .then(r => {
                    if (r && r.message) {
                        frm.set_value("pan_no", r.message.pan);
                    }
                });
        }
    }
});