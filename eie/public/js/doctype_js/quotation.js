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