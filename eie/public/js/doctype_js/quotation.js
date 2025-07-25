if (cur_frm.doc.company == "EIE Instruments Pvt. Ltd.") {
    cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
        return {
            query: "eie.api.new_item_query",
            filters: {
                'dont_allow_sales_in_eie': 0,
                'is_sales_item': 1
            }
        }
    }
} else {
    cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
        return {
            query: "eie.api.new_item_query",
            filters: {
                'is_sales_item': 1
            }
        }
    }
}
erpnext.selling.QuotationController = class QuotationController extends erpnext.selling.QuotationController {
refresh(doc, dt, dn) {
    super.refresh(doc, dt, dn);
    if (doc.company == "EIE Instruments Pvt. Ltd.") {
        cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
            return {
                query: "eie.api.new_item_query",
                filters: {
                    'dont_allow_sales_in_eie': 0,
                    'is_sales_item': 1
                }
            }
        }
    } else {
        cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
            return {
                query: "eie.api.new_item_query",
                filters: {
                    'is_sales_item': 1
                }
            }
        }
    }
}
onload(doc, dt, dn) {
    if (doc.company == "EIE Instruments Pvt. Ltd.") {
        cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
            return {
                query: "eie.api.new_item_query",
                filters: {
                    'dont_allow_sales_in_eie': 0,
                    'is_sales_item': 1
                }
            }
        }
    } else {
        cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
            return {
                query: "eie.api.new_item_query",
                filters: {
                    'is_sales_item': 1
                }
            }
        }
    }
}
naming_series(frm) {
    if (doc.company == "EIE Instruments Pvt. Ltd.") {
        cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
            return {
                query: "eie.api.new_item_query",
                filters: {
                    'dont_allow_sales_in_eie': 0,
                    'is_sales_item': 1
                }
            }
        }
    } else {
        cur_frm.fields_dict["items"].grid.get_field("item_code").get_query = function(doc) {
            return {
                query: "eie.api.new_item_query",
                filters: {
                    'is_sales_item': 1
                }
            }
        }
    }
}
};

cur_frm.script_manager.make(erpnext.selling.QuotationController);

frappe.ui.form.on('Quotation Optional Accessories', {
	before_optional_accessories_remove: function (frm, cdt, cdn) {
		let d = locals [cdt][cdn];
		if (d.essential_accessory){
			frappe.throw(`Item: ${d.accessory} not deleted as same is essential accessory`)
		}
	}
});

frappe.ui.form.on('Quotation', {

    validate: function(frm) {
        let outdated_items = [];
        
        frm.doc.items.forEach(function(item) {
            if (!item.item_code) return;
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Item Price",
                    filters: {
                        price_list: frm.doc.selling_price_list,
                        item_code: item.item_code,
                        selling: 1
                    },
                    fields: ["price_list_rate", "modified","name"],
                    limit_page_length: 1,
                    order_by: "modified desc"
                },
                async: false,
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        let item_price = r.message[0];
                        let last_modified = new Date(r.message[0].modified);
                        let twelve_months_ago = frappe.datetime.add_months(frappe.datetime.now_date(), -12);
                       
                        
                        if (last_modified < new Date(twelve_months_ago)) {
                            outdated_items.push({
                                item_code: item.item_code,
                                item_price_name: item_price.name,
                                idx: item.idx   
                            });
                        }
                    }
                }
            });
        });

        if (outdated_items.length > 0) {
            let items_linked = outdated_items.map(item => {
                let item_price_link = `/app/item-price/${item.item_price_name}`;
                return `Row ${item.idx}:<a href="${item_price_link}" target="_blank" style="text-decoration: underline;">${item.item_code}</a><br>`;
            }).join(", ");
    
            let message = `
                The following items have not had their prices updated in the last 12 months: 
                <br><b>${items_linked}</b><br><br>
            `;
    
            // frappe.msgprint({
            //     title: __('Old Prices Detected'),
            //     message: message,
            //     indicator: 'orange'
            // });
            let dialog = new frappe.ui.Dialog({
                title: __('Old Prices Detected'),
                indicator: 'orange',
                size: 'small',
                primary_action_label: __('Yes'),
                primary_action() {
                    dialog.hide();  // Close when "Yes" clicked
                },
                fields: [
                    {
                        fieldtype: 'HTML',
                        fieldname: 'info',
                        options: `
                            <div>
                                The following items have not had their prices updated in the last 12 months:<br><br>
                                <b>${items_linked}</b><br><br>
                                Please click <b>Yes</b> to close.
                            </div>
                        `
                    }
                ]
            });
        
            dialog.show();
        }
    },
    on_submit: function(frm) {
        let outdated_items = [];
        
        frm.doc.items.forEach(function(item) {
            if (!item.item_code) return;
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Item Price",
                    filters: {
                        price_list: frm.doc.selling_price_list,
                        item_code: item.item_code,
                        selling: 1
                    },
                    fields: ["price_list_rate", "modified","name"],
                    limit_page_length: 1,
                    order_by: "modified desc"
                },
                async: false,
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        let item_price = r.message[0];
                        let last_modified = new Date(r.message[0].modified);
                        let twelve_months_ago = frappe.datetime.add_months(frappe.datetime.now_date(), -12);
                       
                        
                        if (last_modified < new Date(twelve_months_ago)) {
                            outdated_items.push({
                                item_code: item.item_code,
                                item_price_name: item_price.name   
                            });
                        }
                    }
                }
            });
        });

        if (outdated_items.length > 0) {
            let items_linked = outdated_items.map(item => {
                let item_price_link = `/app/item-price/${item.item_price_name}`;  
                return `<a href="${item_price_link}" target="_blank" style="text-decoration: underline;">${item.item_code}</a>`;
            }).join(", ");
    
            let message = `
                The following items have not had their prices updated in the last 12 months: 
                <br><b>${items_linked}</b><br><br>
            `;
    
            frappe.msgprint({
                title: __('Old Prices Detected'),
                message: message,
                indicator: 'orange'
            });
        }
    },

    territory: function(frm) {
        if (frm.doc.party_name) {
            // Fetch the territory manager based on the territory
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Territory",
                    filters: {
                        name: frm.doc.territory
                    },
                    fieldname: "territory_manager"
                },
                callback: function(r) {
                    if (r.message && r.message.territory_manager) {
                        email_func(r.message.territory_manager, frm);

                    } else {
                        // If no territory manager, fetch the sales person based on industry type
                        frappe.call({
                            method: "frappe.client.get_value",
                            args: {
                                doctype: "Industry Type",
                                filters: {
                                    name: frm.doc.industry
                                },
                                fieldname: "sales_person"
                            },
                            callback: function(r) {
                                if (r.message && r.message.sales_person) {
                                    frm.set_value("contact_by", r.message.sales_person);
                                }
                            }
                        });
                    }
                }
            });
        }
    }, 
    onload: function(frm) {
        if (frm.fields_dict['items'] && frm.fields_dict['items'].grid) {
            frm.fields_dict['items'].grid.get_field('warehouse').get_query = function(doc, cdt, cdn) {
                return {
                    filters: {
                        'disabled': 0
                    }
                };
            };
        } else {
            console.error("Child table field or grid not found");
        }
    }
});



 function email_func(manager, frm) {
                        // Fetch the email of the territory manager
                        frappe.call({
                            method: "frappe.client.get_value",
                            args: {
                                doctype: "User",
                                filters: {
                                    full_name: manager
                                },
                                fieldname: "email"
                            },
                            callback: function(r) {
                                if (r.message && r.message.email) {
                                    frm.set_value("contact_by", r.message.email);
                                }
                            }
                        });
    
 };


 frappe.ui.form.on('Quotation', {
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
