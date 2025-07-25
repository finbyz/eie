// frappe.ui.form.on("Delivery Note", {
//     cost_center:function(frm){
//         if(frm.doc.cost_center){
//             frm.doc.items.forEach(d => {
//                 frappe.model.set_value(d.doctype, d.name, 'cost_center', frm.doc.cost_center);
//             });
//         }
//     }
// });

frappe.ui.form.on('Delivery Note', {
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
