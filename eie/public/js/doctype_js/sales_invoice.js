frappe.ui.form.on("Sales Invoice", {
	refresh: function(frm){
        cur_frm.set_query("item_code",'items',function(doc,cdt,cdn){
            if(doc.company == "EIE Instruments Pvt. Ltd."){
                return{
                    filters:{'dont_allow_sales_in_eie':0}
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