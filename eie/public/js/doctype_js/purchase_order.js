{% include "eie/public/js/sms_manager.js" %}


frappe.ui.form.on("Purchase Order", {
    cost_center:function(frm){
        if(frm.doc.cost_center){
            frm.doc.items.forEach(d => {
                frappe.model.set_value(d.doctype, d.name, 'cost_center', frm.doc.cost_center);
            });
        }
    },
    
});
// cur_frm.add_fetch("cost_center", "company", "cost_center");
