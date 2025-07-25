{% include "eie/public/js/sms_manager.js" %}


frappe.ui.form.on("Purchase Order", {
    validate: function(frm) {
        frm.trigger("schedule_date")
    },
    cost_center:function(frm){
        if(frm.doc.cost_center){
            frm.doc.items.forEach(d => {
                if (!d.material_request)
                frappe.model.set_value(d.doctype, d.name, 'cost_center', frm.doc.cost_center);
            });
        }
    },
    schedule_date: function(frm) {
        if (frm.doc.schedule_date) {
            let expire_date = frappe.datetime.add_months(frm.doc.schedule_date, 3);
            frm.set_value('expiry_date', expire_date);
        }
    },


});


cur_frm.set_query("contact_person", function () {
    return {
        query: "frappe.contacts.doctype.contact.contact.contact_query",
        filters: { link_doctype: "Supplier", link_name: cur_frm.doc.supplier }
    };
});
// cur_frm.add_fetch("cost_center", "company", "cost_center");
