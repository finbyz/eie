// Client Script for Chargeable Complaint Entry
// Add this in: Setup > Customization > Client Script

frappe.ui.form.on('Chargeable Complaint Entry', {
    refresh: function(frm) {
        set_sales_invoice_filter(frm);
        set_customer_address_filter(frm);
        set_contact_person_filter(frm);
    },
    
    customer: function(frm) {
        
        frm.clear_table("sales_invoices");
        frm.refresh_field("sales_invoices");
        
        set_sales_invoice_filter(frm);
        set_customer_address_filter(frm);
        set_contact_person_filter(frm);
    },
    customer_address: function(frm) {
        // When customer address changes, auto-fill address display
        if (frm.doc.customer_address) {
            // Method 1: Try ERPNext's built-in address display method
            frappe.call({
                method: 'frappe.contacts.doctype.address.address.get_address_display',
                args: {
                    address_dict: frm.doc.customer_address
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('address_display', r.message);
                    } else {
                        // Method 2: Fallback - manually fetch and format address
                        frappe.call({
                            method: 'frappe.client.get',
                            args: {
                                doctype: 'Address',
                                name: frm.doc.customer_address
                            },
                            callback: function(response) {
                                if (response.message) {
                                    let address_display = get_address_display(response.message);
                                    frm.set_value('address_display', address_display);
                                }
                            }
                        });
                    }
                }
            });
        } else {
            frm.set_value('address_display', '');
        }
    },    
    get_from_sales_invoices: function(frm) {
        // Check if document is saved
        if (frm.doc.__islocal) {
            frappe.msgprint(__('Please save the document first before getting items from Sales Invoices.'));
            return;
        }
        
        // Call the server-side method
        frappe.call({
            method: 'get_items_from_sales_invoices',
            doc: frm.doc,
            callback: function(response) {
                if (response.message) {
                    // Refresh the form to show updated items
                    frm.reload_doc();
                }
            },
            error: function(error) {
                frappe.msgprint(__('Error getting items from Sales Invoices: ') + error.message);
            }
        });
    }
});

frappe.ui.form.on('CCE Sales Invoice', { 
    
    sales_invoices_add: function(frm, cdt, cdn) { 
        set_sales_invoice_filter(frm, cdt, cdn);
    },
    sales_invoice: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (row.sales_invoice) {
            let is_first_row = row.idx === 1;
            let parent_fields_empty = !frm.doc.customer_address || !frm.doc.contact_person;
            let should_fill_parent = is_first_row || parent_fields_empty;
            
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Sales Invoice',
                    name: row.sales_invoice
                },
                callback: function(r) {
                    if (r.message) {
                        let sales_invoice = r.message;
                        
                        if (should_fill_parent) {
                            
                        
                            let has_address = sales_invoice.customer_address && sales_invoice.address_display;
                            let has_contact = sales_invoice.contact_person || sales_invoice.contact_mobile || sales_invoice.contact_email;
                            
                            
                            if (has_address || has_contact) {
                                if (sales_invoice.customer_address) {
                                    frm.set_value('customer_address', sales_invoice.customer_address);
                                }
                                if (sales_invoice.address_display) {
                                    frm.set_value('address_display', sales_invoice.address_display);
                                }
                                if (sales_invoice.contact_person) {
                                    frm.set_value('contact_person', sales_invoice.contact_person);
                                }
                                if (sales_invoice.contact_mobile) {
                                    frm.set_value('contact_number', sales_invoice.contact_mobile);
                                }
                                if (sales_invoice.contact_email) {
                                    frm.set_value('contact_email', sales_invoice.contact_email);
                                }
                            }
                        }
                    }
                }
            });
        }
    }
});

function set_sales_invoice_filter(frm) {
    if (frm.doc.customer) { 
        frm.set_query("sales_invoice", "sales_invoices", function() {
            return {
                "filters": {
                    "customer": frm.doc.customer,
                }
            };
        });
    }
}

function set_customer_address_filter(frm) {
    if (frm.doc.customer) {
        frm.set_query("customer_address", function() {
            return {
                "filters": [
                    ["Dynamic Link", "link_doctype", "=", "Customer"],
                    ["Dynamic Link", "link_name", "=", frm.doc.customer]
                ]
            };
        });
    }
}

function set_contact_person_filter(frm) {
    if (frm.doc.customer) {
        frm.set_query("contact_person", function() {
            return {
                "filters": [
                    ["Dynamic Link", "link_doctype", "=", "Customer"],
                    ["Dynamic Link", "link_name", "=", frm.doc.customer]
                ]
            };
        });
    }
}

function get_address_display(address) {
    // Function to format address display manually if needed
    let address_parts = [];
    if (address.address_line1) address_parts.push(address.address_line1);
    if (address.address_line2) address_parts.push(address.address_line2);
    if (address.city) address_parts.push(address.city);
    if (address.state) address_parts.push(address.state);
    if (address.country) address_parts.push(address.country);
    if (address.pincode) address_parts.push(address.pincode);
    
    return address_parts.join(', ');
}