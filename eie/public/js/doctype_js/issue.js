
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
 
        // let employees_ready = false;
        // // Temporary filter: return empty until ready
        // frm.fields_dict["sale_invoice_issue_item"].grid.get_field("employees").get_query = function () {
        //     if (!employees_ready) {
        //         return { filters: [["Employee", "name", "=", ""]] }; // will show nothing
        //     }
        // };

        // // Call server
        // frappe.call({
        //     method: "eie.eie.doc_events.issue.get_service_engineers",
        //     callback: function (r) {
        //         if (r.message) {
        //             employees_ready = true;
        //             frm.fields_dict["sale_invoice_issue_item"].grid.get_field("employees").get_query = function () {
        //                 return { filters: [["Employee", "name", "in", r.message]] };
        //             };
        //         }
               
        //     }
        // });
        // //  frm.refresh_field("sale_invoice_issue_item");
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
                        child.employees = item.service_engineers;
                    });
                    
                    frm.refresh_field('sales_invoice_issue_items');
                }
            },
            error: function(err) {
                frappe.msgprint(__('There was an error fetching Sales Invoice items.'));
                console.error(err);
            }
        });
        // add_employee_filter_item(frm);
    }
});

//Ritik changes
function set_employee_filter(frm, employees_list) {
    // Apply filter
    frm.fields_dict["sale_invoice_issue_item"].grid.get_field("employees").get_query = function (doc, cdt, cdn) {
        return {
            filters: [["Employee", "name", "in", employees_list]]
        };
    };

    // Enable field only after filter is set
    frm.fields_dict["sale_invoice_issue_item"].grid.get_field("employees").df.read_only = 0;
    frm.refresh_field("sale_invoice_issue_item");
}

// frappe.ui.form.on('Sales Invoice issue Item', {
//     refresh: function(frm) {
//         if (frm.doc.sales_invoice) {
//             frm.set_query('employee', function() {
//                 return {
//                     filters: {
//                         name: frm.doc.sales_invoice
//                     }
//                 };
//             });
//         }
//     }
// });