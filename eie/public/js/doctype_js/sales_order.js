cur_frm.add_fetch("item_code", "specification", "specification");

//For Storing Main Item for selection
let item_list = [];

//Add searchfield to Item query


cur_frm.fields_dict.taxes_and_charges.get_query = function (doc) {
	return {
		"filters": {
			'company': doc.company
		}
	};
}

// Fetch Terms and Condition
cur_frm.add_fetch("tc_name", "terms", "terms");

// Set Filter on select_item field
/*cur_frm.fields_dict['select_item'].get_query = function(doc) {
	// console.log(item_list);
	return {
		"filters": [
			["Item", "item_code", "in", item_list]
		]
	};
};


cur_frm.fields_dict.items.grid.get_field("main_item").get_query = function(doc) {
	return {
		"filters": [
			["Item", "item_code", "in", item_list]
		]
	};
};*/

//Fetch data From Employee.

cur_frm.add_fetch("store_contact", "email_id", "store_person_email_id");
cur_frm.add_fetch("user_contact", "email_id", "user_email_id");
//fetch account type
cur_frm.add_fetch("bank_account", "account_type", "account_type");
//Contact Filter
cur_frm.set_query("store_contact", function () {
	if (cur_frm.doc.customer) {
		return {
			query: "frappe.contacts.doctype.contact.contact.contact_query",
			filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
		};
	}
	else frappe.throw(__("Please set Customer"));
});

cur_frm.set_query("user_contact", function () {
	if (cur_frm.doc.customer) {
		return {
			query: "frappe.contacts.doctype.contact.contact.contact_query",
			filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
		};
	}
	else frappe.throw(__("Please set Customer"));
});

//Filter Customer Address
cur_frm.set_query("customer_address", function () {
	return {
		query: "frappe.contacts.doctype.address.address.address_query",
		filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
	};
});

//Filter Shipping Address
cur_frm.set_query("shipping_address_name", function () {
	return {
		query: "frappe.contacts.doctype.address.address.address_query",
		filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
	};
});

// Override Material Request Mapping
// cur_frm.cscript.make_material_request = function(frm){
// 	frappe.model.open_mapped_doc({
// 		method: "eie.api.make_material_request",
// 		frm: cur_frm
// 	})
// }

cur_frm.cscript.make_material_request = function (frm) {
	frappe.call({
		method: "eie.api.make_material_request",
		args: {
			"source_name": cur_frm.doc.name,
		},
	})
}

// Contact Query Filter
cur_frm.set_query("contact_person", function () {

	return {
		query: "frappe.contacts.doctype.contact.contact.contact_query",
		filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
	};

});


erpnext.utils.update_child_items = function (opts) {
	const frm = opts.frm;
	const cannot_add_row = (typeof opts.cannot_add_row === 'undefined') ? true : opts.cannot_add_row;
	const child_docname = (typeof opts.cannot_add_row === 'undefined') ? "items" : opts.child_docname;
	this.data = [];
	let me = this;
	const dialog = new frappe.ui.Dialog({
		title: __("Update Items"),
		fields: [
			{
				fieldname: "trans_items",
				fieldtype: "Table",
				label: "Items",
				cannot_add_rows: cannot_add_row,
				in_place_edit: true,
				reqd: 1,
				data: this.data,
				get_data: () => {
					return this.data;
				},
				fields: [{
					fieldtype: 'Data',
					fieldname: "docname",
					read_only: 1,
					hidden: 1,
				}, {
					fieldtype: 'Link',
					fieldname: "item_code",
					options: 'Item',
					in_list_view: 1,
					read_only: 0,
					disabled: 0,
					columns: 3,
					label: __('Item Code'),
					// change: function () {
					//     let trans_items = cur_dialog.fields_dict.trans_items;
					//     let me2 = this;
					//     if (this.doc.item_code) {
					//         console.log('update item')
					//     }
					// }
				}, {
					fieldtype: 'Float',
					fieldname: "qty",
					default: 0,
					read_only: 0,
					in_list_view: 1,
					columns: 1,
					label: __('Qty')
				}, {
					fieldtype: 'Currency',
					fieldname: "rate",
					read_only: 0,
					in_list_view: 1,
					reqd: 1,
					// columns: 1,
					permlevel: 2,
					label: __('Rate')
				}, {
					fieldtype: 'Currency',
					fieldname: "original_rate",
					read_only: 0,
					in_list_view: 1,
					reqd: 1,
					// columns: 1,
					permlevel: 2,
					label: __('Original Rate')
				}]
			},
		],
		primary_action: function () {
			const trans_items = this.get_values()["trans_items"];
			for (var d of trans_items) {
				if (d['rate'] == 0.00) {
					frappe.throw('Please enter rate')
				}
			}

			frappe.call({
				method: 'eie.update_item.update_child_qty_rate',
				freeze: true,
				args: {
					'parent_doctype': frm.doc.doctype,
					'trans_items': trans_items,
					'parent_doctype_name': frm.doc.name,
					'child_docname': child_docname
				},
				callback: function () {
					frm.reload_doc();
				}
			});
			this.hide();
			refresh_field("items");
		},
		primary_action_label: __('Update')
	});

	frm.doc[opts.child_docname].forEach(d => {
		dialog.fields_dict.trans_items.df.data.push({
			"docname": d.name,
			"name": d.name,
			"item_code": d.item_code,
			"delivery_date": d.delivery_date,
			"schedule_date": d.schedule_date,
			"conversion_factor": d.conversion_factor,
			"qty": d.qty,
			"rate": d.rate,
			"original_rate": d.original_rate,
		});
		this.data = dialog.fields_dict.trans_items.df.data;
		dialog.fields_dict.trans_items.grid.refresh();
	})
	dialog.show();
}


frappe.ui.form.on("Sales Order", {
	cost_center: function (frm) {
		if (frm.doc.cost_center) {
			frm.doc.items.forEach(d => {
				frappe.model.set_value(d.doctype, d.name, 'cost_center', frm.doc.cost_center);
			});
		}
	},
	store_contact: function (frm) {
		if (cur_frm.doc.store_contact == undefined) {
			frm.set_value("store_person", '');
			frm.set_value("store_person_mobile_no", '');
			frm.set_value("store_person_phone", '');
			frm.set_value("store_person_email_id", '');
		}
	},
	refresh: function (frm) {
		frm.trigger("change_subitem_color");
		frm.trigger("update_item_list");
	},
	demonstration_required: function (frm) {
		if (frm.doc.demonstration_required) {
			frm.doc.items.forEach(function (d) {
				frappe.model.set_value(d.doctype, d.name, 'demonstration_req', 1);
			});
		} else {
			frm.doc.items.forEach(function (d) {
				frappe.model.set_value(d.doctype, d.name, 'demonstration_req', 0);
			});
		}
	},
	onload: function (frm) {
		if (frm.doc.__islocal) {
			frm.set_value("tc_name", "Sales Order Conditions");
		}
	},

	validate: function (frm) {
		if (frm.doc.po_date) {
			if (frm.doc.po_date.split('-')[0] < '2000') {
				frappe.throw(__("The Customer's Purchase Order Date is less than 2000."))
			}
		}
	},

	before_save: function (frm) {
		if (frm.doc.items[0].prevdoc_docname) {
			frappe.db.get_value("Quotation", { 'name': frm.doc.items[0].prevdoc_docname }, 'owner', function (r) {

				frm.set_value("quotation_prepared_by", r.owner);
			});
		}

		frm.trigger("calculate_unhedge");
		frm.doc.items.forEach(function (d) {
			// rate changes issue
			if (d.rate > d.price_list_rate && (!d.discount_amount < 0)) {
				frappe.model.set_value(d.doctype, d.name, 'discount_amount', 0);
			}
			else if (d.rate > d.price_list_rate && (d.discount_amount < 0)) {
				if (!d.margin_rate_or_amount) {
					frappe.model.set_value(d.doctype, d.name, 'margin_type', 'Amount');
					frappe.model.set_value(d.doctype, d.name, 'margin_rate_or_amount', flt(d.rate - d.price_list_rate));
					frappe.model.set_value(d.doctype, d.name, 'discount_percentage', 0);
					frappe.model.set_value(d.doctype, d.name, 'discount_amount', 0);
				}
			}
		})
	},

	grand_total: function (frm) {
		frm.trigger("calculate_unhedge");
	},

	natural_hedge: function (frm) {
		frm.trigger("calculate_unhedge");
	},

	/* Function to Calculate Amount Unhedged
		Called on Events: grand_total, before_save, natural_hedge (Parent)
	*/
	calculate_unhedge: function (frm) {
		if (frm.doc.currency != "INR") {
			let unhedge = flt(frm.doc.grand_total) - flt(frm.doc.amount_hedged) - flt(frm.doc.advance_paid) - flt(frm.doc.natural_hedge);
			frm.set_value("amount_unhedged", unhedge);
		}
	},

	/* Function for changing color for sub items
		Called on Events: 
			refresh (Parent)
			item_code, main_item, items_remove (Sales Order Item)
	*/
	change_subitem_color: function (frm) {
		frm.doc.items.forEach(function (row) {
			if (row.main_item) {
				$("div[data-fieldname='items']").find($.format('div.grid-row[data-idx="{0}"]', [row.idx])).css({ 'background-color': '#eedcef' });
				$("div[data-fieldname='items']").find($.format('div.grid-row[data-idx="{0}"]', [row.idx])).find('.grid-static-col').css({ 'background-color': '#eedcef' });
			}
			else {
				$("div[data-fieldname='items']").find($.format('div.grid-row[data-idx="{0}"]', [row.idx])).css({ 'background-color': 'transparent' });
				$("div[data-fieldname='items']").find($.format('div.grid-row[data-idx="{0}"]', [row.idx])).find('.grid-static-col').css({ 'background-color': 'transparent' });
			}
		});
	},

	// Remove Item Spares and Accessories on Remove button click
	remove_btn: function (frm) {
		if (frm.doc.select_item) {
			item_list = [];
			frm.doc.items.forEach(function (row) {
				let i = row.idx - 1;
				if (row.main_item == frm.doc.select_item) {
					frm.get_field("items").grid.grid_rows[i].remove();
				}
				else {
					item_list.push(row.item_code);
				}
			});
		}
		else {
			let items = frm.doc.items;
			let len = items.length;

			while (len--) {
				if (items[len].main_item) {
					frm.get_field("items").grid.grid_rows[len].remove();
				}
			}
		}
		frm.refresh_field("items");
		frm.set_value("select_item", "");
		frm.trigger('update_item_list');
	},

	/*Function to insert main_item in item_list
		Called on events:
			on_load, remove_btn (Parent)
			item_code, main_item, items_remove (Sales Order Item)
	*/
	update_item_list: function (frm) {
		item_list = [];
		frm.doc.items.forEach(function (row) {
			if (!row.main_item) {
				item_list.push(row.item_code);
			}
		});
	},

	discount: function (frm) {
		frm.doc.items.forEach(function (row) {
			frappe.model.set_value(row.doctype, row.name, 'discount_per', frm.doc.discount);
		});
		frm.refresh_field('items');
	},
	//Add actualcustomer of each item.
	actual_customer: function (frm) {
		frm.doc.items.forEach(function (d) {
			frappe.model.set_value(d.doctype, d.name, 'actual_customer', frm.doc.actual_customer);
		});
		frm.refresh_field('items');
	},
});

frappe.ui.form.on("Sales Order Item", {
	item_code: function (frm, cdt, cdn) {

		frm.events.change_subitem_color(frm);
		frm.events.update_item_list(frm);

		let m = locals[cdt][cdn];
		if (m.item_code) {
			frappe.model.with_doc("Item", m.item_code, function () {
				let qmtable = frappe.model.get_doc("Item", m.item_code);
				// var item_list =[]
				//             frm.doc.items.forEach(function(d){
				//                 if(!item_list.includes(d.item_code))
				//                     item_list.push(d.item_code)
				//             })
				//             console.log(item_list)
				var spares_list = []
				if (frm.doc.items) {
					frm.doc.items.forEach(function (row) {
						if (!spares_list.includes(row.item_code)) {
							spares_list.push(row.item_code)
						}
					});
				}
				// Add Item Spares in Sales Order Item Table
				qmtable.spares.forEach(function (row) {
					if (!spares_list.includes(row.spare)) {
						let d = frappe.model.add_child(frm.doc, "Sales Order Item", "items");
						frappe.model.set_value(d.doctype, d.name, 'item_code', row.spare);
						frappe.model.set_value(d.doctype, d.name, 'main_item', m.item_code);
					}
				});

				var optional_accessories_list = []
				if (frm.doc.items) {
					frm.doc.items.forEach(function (row) {
						if (!optional_accessories_list.includes(row.item_code)) {
							optional_accessories_list.push(row.item_code)
						}
					});
				}
				// console.log(optional_accessories_list)
				// Add Item Optional Accessories in Sales Order Item Table
				qmtable.optional_accessories.forEach(function (row) {
					if (!spares_list.includes(row.accessory)) {
						let d = frappe.model.add_child(frm.doc, "Sales Order Item", "items");
						frappe.model.set_value(d.doctype, d.name, 'item_code', row.accessory);
						frappe.model.set_value(d.doctype, d.name, 'main_item', m.item_code);
					}
				});

				frm.refresh_field("items");
			});
		}
	},


	main_item: function (frm, cdt, cdn) {
		frm.events.update_item_list(frm);
		frm.events.change_subitem_color(frm);
	},

	items_remove: function (frm, cdt, cdn) {
		frm.events.update_item_list(frm);
		frm.events.change_subitem_color(frm);
	},

	price_list_rate: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (d.price_list_rate && !d.original_rate) {
			frappe.model.set_value(cdt, cdn, 'original_rate', d.price_list_rate);
		}
	},

	rate: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];

		if (!d.price_list_rate) {
			d.price_list_rate = d.rate;
		}
	},
	original_rate: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		let disc = flt(d.original_rate * d.discount_per, precision("discount_per", d)) / 100.0;
		let rate = flt(d.original_rate, precision("original_rate", d)) - flt(disc, precision("discount_per", d));
		frappe.model.set_value(cdt, cdn, 'rate', flt(rate, precision("rate", d)));
	},
	discount_per: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		let disc = flt(d.original_rate * d.discount_per, precision("discount_per", d)) / 100.0;
		let rate = flt(d.original_rate, precision("original_rate", d)) - flt(disc, precision("discount_per", d));
		frappe.model.set_value(cdt, cdn, 'rate', flt(rate, precision("rate", d)));
	}
});


// frappe.ui.form.on('Sales Order', {
//     refresh: function (frm) {
//         highlight_child_table_rows(frm);
// 		highlight_child_table_packed_items_rows(frm); 
//     },
//     onload_post_render: function (frm) {
//         frm.fields_dict['items'].grid.wrapper.on('click', '.grid-row', function () {
//             highlight_child_table_rows(frm);
// 			highlight_child_table_packed_items_rows(frm);
//         });

//         frm.fields_dict['items'].grid.wrapper.on('change', function () {
//             highlight_child_table_rows(frm);
// 			highlight_child_table_packed_items_rows(frm);
//         });

//         highlight_child_table_rows(frm); // Initial highlighting
// 		highlight_child_table_packed_items_rows(frm);
//     }

	
// });

// function highlight_child_table_rows(frm) {  
// 	if (!frm.doc.__islocal  && frm.doc.status === 'To Bill'){
// 		frappe.call({
// 			method: 'eie.eie.doc_events.sales_order.highlight_sales_order_items',
// 			args: {
// 				sales_order_name: frm.doc.name
// 			},
// 			callback: function (response) {
// 				if (response.message) {
// 					frm.fields_dict['items'].grid.grid_rows.forEach(row => {
// 						if (response.message.includes(row.doc.idx)) {
// 							$(row.row).css('background-color', '#ffcc00'); // Highlight matching rows
// 						} else {
// 							$(row.row).css('background-color', ''); // Remove highlight for non-matching rows
// 						}
// 					});
// 				}
// 			}
// 		});
// 	}
// }


// function highlight_child_table_packed_items_rows(frm) {  
// 	if (!frm.doc.__islocal  && frm.doc.status === 'To Bill'	){
//     frappe.call({
//         method: 'eie.eie.doc_events.sales_order.highlight_sales_order_packed_items',
//         args: {
//             sales_order_name: frm.doc.name
//         },
//         callback: function (response) {
//             if (response.message) {
//                 frm.fields_dict['packed_items'].grid.grid_rows.forEach(row => {
//                     if (response.message.includes(row.doc.idx)) {
//                         $(row.row).css('background-color', '#ffcc00'); 
//                     } else {
//                         $(row.row).css('background-color', '')
//                     }
//                 });
//             }
//         }
//     });}
// }

frappe.ui.form.on('Sales Order', {
    // before_submit: function (frm) {
    //     highlight_child_table_rows(frm);
    //     highlight_child_table_packed_items_rows(frm); 
    // },
    // onload_post_render: function (frm) {
    //     frm.fields_dict['items'].grid.wrapper.on('click', '.grid-row', function () {
    //         highlight_child_table_rows(frm);
    //         highlight_child_table_packed_items_rows(frm);
    //     });

    //     frm.fields_dict['items'].grid.wrapper.on('change', function () {
    //         highlight_child_table_rows(frm);
    //         highlight_child_table_packed_items_rows(frm);
    //     });

    //     highlight_child_table_rows(frm); // Initial highlighting
    //     highlight_child_table_packed_items_rows(frm);
    // }
	refresh: function (frm) {
        if (frm.doc.docstatus === 1) { // Only trigger for submitted Sales Orders
            highlight_child_table_rows(frm);
            highlight_child_table_packed_items_rows(frm);
        }
    }
});

function is_not_draft_cancelled_or_closed(frm) {
    return !frm.doc.__islocal && !['Draft', 'Cancelled', 'Closed'].includes(frm.doc.status);
}

// function highlight_child_table_rows(frm) {
//     if (is_not_draft_cancelled_or_closed(frm)) {
//         frappe.call({
//             method: 'eie.eie.doc_events.sales_order.highlight_sales_order_items',
//             args: {
//                 sales_order_name: frm.doc.name
//             },
//             callback: function (response) {
//                 if (response.message) {
//                     frm.fields_dict['items'].grid.grid_rows.forEach(row => {
//                         if (response.message.includes(row.doc.idx)) {
//                             $(row.row).css('background-color', '#ffcc00'); // Highlight matching rows
//                         } else {
//                             $(row.row).css('background-color', ''); // Remove highlight for non-matching rows
//                         }
//                     });
//                 }
//             }
//         });
//     }
// }

// function highlight_child_table_packed_items_rows(frm) {
//     if (is_not_draft_cancelled_or_closed(frm)) {
//         frappe.call({
//             method: 'eie.eie.doc_events.sales_order.highlight_sales_order_packed_items',
//             args: {
//                 sales_order_name: frm.doc.name
//             },
//             callback: function (response) {
//                 if (response.message) {
//                     frm.fields_dict['packed_items'].grid.grid_rows.forEach(row => {
//                         if (response.message.includes(row.doc.idx)) {
//                             $(row.row).css('background-color', '#ffcc00'); // Highlight matching rows
//                         } else {
//                             $(row.row).css('background-color', ''); // Remove highlight for non-matching rows
//                         }
//                     });
//                 }
//             }
//         });
//     }
// }

function highlight_child_table_rows(frm) {
    frappe.call({
        method: 'eie.eie.doc_events.sales_order.highlight_sales_order_items',
        args: {
            sales_order_name: frm.doc.name
        },
        callback: function (response) {
            if (response.message) {
                frm.fields_dict['items'].grid.grid_rows.forEach(row => {
                    if (response.message.includes(row.doc.idx)) {
                        $(row.row).css('background-color', '#ffcc00'); // Highlight matching rows
                    } else {
                        $(row.row).css('background-color', ''); // Reset non-matching rows
                    }
                });
            }
        }
    });
}

function highlight_child_table_packed_items_rows(frm) {
    frappe.call({
        method: 'eie.eie.doc_events.sales_order.highlight_sales_order_packed_items',
        args: {
            sales_order_name: frm.doc.name
        },
        callback: function (response) {
            if (response.message) {
                frm.fields_dict['packed_items'].grid.grid_rows.forEach(row => {
                    if (response.message.includes(row.doc.idx)) {
                        $(row.row).css('background-color', '#ffcc00'); // Highlight matching rows
                    } else {
                        $(row.row).css('background-color', ''); // Reset non-matching rows
                    }
                });
            }
        }
    });
}
