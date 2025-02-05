
frappe.ui.form.on('Issue', {
    refresh: function(frm) {
        if (frm.doc.customer) {  
            frm.set_query('sales_invoice', function() {
                return {
                    filters: {
                        'customer': frm.doc.customer, 
                        'docstatus': 1 
                    }
                };
            });
        }
    },
    get_sales_invoice_items: function(frm) {
        // console.log('Selected Sales Invoices:', frm.doc.sales_invoice);
        frappe.call({
            method: 'eie.eie.doc_events.issue.get_sales_invoice_items',
            args: {
                sales_invoice_list: frm.doc.sales_invoice  
            },
            callback: function(r) {
                if (r.message) {
                    frm.clear_table('sales_invoice_issue_items');
                    
                    r.message.forEach(function(item) {
                        let child = frm.add_child('sales_invoice_issue_items');
                        child.item_code = item.item_code;
                        child.qty = item.qty;
                        child.sales_invoice_no = item.sales_invoice_no;
                        child.date = item.date;
                    });
                    
                    frm.refresh_field('sales_invoice_issue_items');
                }
            },
            error: function(err) {
                frappe.msgprint(__('There was an error fetching Sales Invoice items.'));
                console.error(err);
            }
        });
    }
});