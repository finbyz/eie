erpnext.selling.SalesOrderController = erpnext.selling.SellingController.extend({
	onload: function(doc, dt, dn) {
		this._super();
	},
	
	refresh: function(doc, dt, dn) {
		var me = this;
		this._super();
		let allow_delivery = false;
		
		if (doc.docstatus==1) {

			if(this.frm.has_perm("submit")) {
				if(doc.status === 'On Hold') {
				   // un-hold
				   this.frm.add_custom_button(__('Resume'), function() {
					   me.frm.cscript.update_status('Resume', 'Draft')
				   }, __("Status"));

				   if(flt(doc.per_delivered, 6) < 100 || flt(doc.per_billed) < 100) {
					   // close
					   this.frm.add_custom_button(__('Close'), () => this.close_sales_order(), __("Status"))
				   }
				}
			   	else if(doc.status === 'Closed') {
				   // un-close
				   this.frm.add_custom_button(__('Re-open'), function() {
					   me.frm.cscript.update_status('Re-open', 'Draft')
				   }, __("Status"));
			   }
			}
			if(doc.status !== 'Closed') {
				if(doc.status !== 'On Hold') {
					allow_delivery = this.frm.doc.items.some(item => item.delivered_by_supplier === 0 && item.qty > flt(item.delivered_qty))
						&& !this.frm.doc.skip_delivery_note

					if (this.frm.has_perm("submit")) {
						if(flt(doc.per_delivered, 6) < 100 || flt(doc.per_billed) < 100) {
							// hold
							this.frm.add_custom_button(__('Hold'), () => this.hold_sales_order(), __("Status"))
							// close
							this.frm.add_custom_button(__('Close'), () => this.close_sales_order(), __("Status"))
						}
					}

					this.frm.add_custom_button(__('Pick List'), () => this.create_pick_list(), __('Create'));

					// delivery note
					if(flt(doc.per_delivered, 6) < 100 && ["Sales", "Shopping Cart"].indexOf(doc.order_type)!==-1 && allow_delivery) {
						this.frm.add_custom_button(__('Delivery Note'), () => this.make_delivery_note_based_on_delivery_date(), __('Create'));
						this.frm.add_custom_button(__('Work Order'), () => this.make_work_order(), __('Create'));
					}

					// sales invoice
					if(flt(doc.per_billed, 6) < 100) {
						this.frm.add_custom_button(__('Invoice'), () => me.make_sales_invoice(), __('Create'));
					}

					// material request
					if(!doc.order_type || ["Sales", "Shopping Cart"].indexOf(doc.order_type)!==-1
						&& flt(doc.per_delivered, 6) < 100) {
						this.frm.add_custom_button(__('Material Request'), () => me.make_material_request(), __('Create'));
						this.frm.add_custom_button(__('Request for Raw Materials'), () => this.make_raw_material_request(), __('Create'));
					}

					// make purchase order
						this.frm.add_custom_button(__('Purchase Order'), () => this.make_purchase_order(), __('Create'));

					// maintenance
					if(flt(doc.per_delivered, 2) < 100 &&
							["Sales", "Shopping Cart"].indexOf(doc.order_type)===-1) {
						this.frm.add_custom_button(__('Maintenance Visit'), () => this.make_maintenance_visit(), __('Create'));
						this.frm.add_custom_button(__('Maintenance Schedule'), () => this.make_maintenance_schedule(), __('Create'));
					}

					// project
					if(flt(doc.per_delivered, 2) < 100 && ["Sales", "Shopping Cart"].indexOf(doc.order_type)!==-1 && allow_delivery) {
							this.frm.add_custom_button(__('Project'), () => this.make_project(), __('Create'));
					}

					if(!doc.auto_repeat) {
						this.frm.add_custom_button(__('Subscription'), function() {
							erpnext.utils.make_subscription(doc.doctype, doc.name)
						}, __('Create'))
					}

					if (doc.docstatus === 1 && !doc.inter_company_order_reference) {
						let me = this;
						frappe.model.with_doc("Customer", me.frm.doc.customer, () => {
							let customer = frappe.model.get_doc("Customer", me.frm.doc.customer);
							let internal = customer.is_internal_customer;
							let disabled = customer.disabled;
							if (internal === 1 && disabled === 0) {
								me.frm.add_custom_button("Inter Company Order", function() {
									me.make_inter_company_order();
								}, __('Create'));
							}
						});
					}
				}
				// payment request
				if(flt(doc.per_billed)<100) {
					this.frm.add_custom_button(__('Payment Request'), () => this.make_payment_request(), __('Create'));
					this.frm.add_custom_button(__('Payment'), () => this.make_payment_entry(), __('Create'));
				}
				this.frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}

		if (this.frm.doc.docstatus===0) {
			this.frm.add_custom_button(__('Quotation'),
				function() {
					erpnext.utils.map_current_doc({
						method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
						source_doctype: "Quotation",
						target: me.frm,
						setters: [
							{
								label: "Customer",
								fieldname: "party_name",
								fieldtype: "Link",
								options: "Customer",
								default: me.frm.doc.customer || undefined
							}
						],
						get_query_filters: {
							company: me.frm.doc.company,
							docstatus: 1,
							status: ["!=", "Lost"]
						}
					})
				}, __("Get items from"));
		}

		this.order_type(doc);
		cur_frm.set_query("item_code", "items", function(doc) {
			if(doc.company == "EIE Instruments Pvt. Ltd."){
				return{
					query: "eie.api.new_item_query",
					filters:{'dont_allow_sales_in_eie':0,'is_sales_item': 1}
				}
			}
			else{
				return {
					query: "eie.api.new_item_query",
					filters: {'is_sales_item': 1}
				}
			}
			
		});
		
		cur_frm.set_query("bank_account", "bank_accounts", function(doc) {
			return {
				filters: {
					"company": doc.company
				}
			}
		});
	},

	create_pick_list() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.create_pick_list",
			frm: this.frm
		})
	},

	make_work_order() {
		var me = this;
		this.frm.call({
			doc: this.frm.doc,
			method: 'get_work_order_items',
			callback: function(r) {
				if(!r.message) {
					frappe.msgprint({
						title: __('Work Order not created'),
						message: __('No Items with Bill of Materials to Manufacture'),
						indicator: 'orange'
					});
					return;
				}
				else if(!r.message) {
					frappe.msgprint({
						title: __('Work Order not created'),
						message: __('Work Order already created for all items with BOM'),
						indicator: 'orange'
					});
					return;
				} else {
					const fields = [{
						label: 'Items',
						fieldtype: 'Table',
						fieldname: 'items',
						description: __('Select BOM and Qty for Production'),
						fields: [{
							fieldtype: 'Read Only',
							fieldname: 'item_code',
							label: __('Item Code'),
							in_list_view: 1
						}, {
							fieldtype: 'Link',
							fieldname: 'bom',
							options: 'BOM',
							reqd: 1,
							label: __('Select BOM'),
							in_list_view: 1,
							get_query: function (doc) {
								return { filters: { item: doc.item_code } };
							}
						}, {
							fieldtype: 'Float',
							fieldname: 'pending_qty',
							reqd: 1,
							label: __('Qty'),
							in_list_view: 1
						}, {
							fieldtype: 'Data',
							fieldname: 'sales_order_item',
							reqd: 1,
							label: __('Sales Order Item'),
							hidden: 1
						}],
						data: r.message,
						get_data: () => {
							return r.message
						}
					}]
					var d = new frappe.ui.Dialog({
						title: __('Select Items to Manufacture'),
						fields: fields,
						primary_action: function() {
							var data = d.get_values();
							me.frm.call({
								method: 'make_work_orders',
								args: {
									items: data,
									company: me.frm.doc.company,
									sales_order: me.frm.docname,
									project: me.frm.project
								},
								freeze: true,
								callback: function(r) {
									if(r.message) {
										frappe.msgprint({
											message: __('Work Orders Created: {0}',
												[r.message.map(function(d) {
													return repl('<a href="#Form/Work Order/%(name)s">%(name)s</a>', {name:d})
												}).join(', ')]),
											indicator: 'green'
										})
									}
									d.hide();
								}
							});
						},
						primary_action_label: __('Create')
					});
					d.show();
				}
			}
		});
	},

	order_type: function() {
		this.toggle_delivery_date();
	},

	tc_name: function() {
		this.get_terms();
	},

	// make_material_request: function() {
	// 	frappe.model.open_mapped_doc({
	// 		method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
	// 		frm: this.frm
	// 	})
	// },

	make_material_request: function() {
		frappe.call({
			method : "eie.api.make_material_request",
			args: {
				"source_name": cur_frm.doc.name,
			},
		})
	},

	skip_delivery_note: function() {
		this.toggle_delivery_date();
	},

	toggle_delivery_date: function() {
		this.frm.fields_dict.items.grid.toggle_reqd("delivery_date",
			(this.frm.doc.order_type == "Sales" && !this.frm.doc.skip_delivery_note));
	},

	make_raw_material_request: function() {
		var me = this;
		this.frm.call({
			doc: this.frm.doc,
			method: 'get_work_order_items',
			args: {
				for_raw_material_request: 1
			},
			callback: function(r) {
				if(!r.message) {
					frappe.msgprint({
						message: __('No Items with Bill of Materials.'),
						indicator: 'orange'
					});
					return;
				}
				else {
					me.make_raw_material_request_dialog(r);
				}
			}
		});
	},

	make_raw_material_request_dialog: function(r) {
		var fields = [
			{fieldtype:'Check', fieldname:'include_exploded_items',
				label: __('Include Exploded Items')},
			{fieldtype:'Check', fieldname:'ignore_existing_ordered_qty',
				label: __('Ignore Existing Ordered Qty')},
			{
				fieldtype:'Table', fieldname: 'items',
				description: __('Select BOM, Qty and For Warehouse'),
				fields: [
					{fieldtype:'Read Only', fieldname:'item_code',
						label: __('Item Code'), in_list_view:1},
					{fieldtype:'Link', fieldname:'warehouse', options: 'Warehouse',
						label: __('For Warehouse'), in_list_view:1},
					{fieldtype:'Link', fieldname:'bom', options: 'BOM', reqd: 1,
						label: __('BOM'), in_list_view:1, get_query: function(doc) {
							return {filters: {item: doc.item_code}};
						}
					},
					{fieldtype:'Float', fieldname:'required_qty', reqd: 1,
						label: __('Qty'), in_list_view:1},
				],
				data: r.message,
				get_data: function() {
					return r.message
				}
			}
		]
		var d = new frappe.ui.Dialog({
			title: __("Items for Raw Material Request"),
			fields: fields,
			primary_action: function() {
				var data = d.get_values();
				me.frm.call({
					method: 'erpnext.selling.doctype.sales_order.sales_order.make_raw_material_request',
					args: {
						items: data,
						company: me.frm.doc.company,
						sales_order: me.frm.docname,
						project: me.frm.project
					},
					freeze: true,
					callback: function(r) {
						if(r.message) {
							frappe.msgprint(__('Material Request {0} submitted.',
							['<a href="#Form/Material Request/'+r.message.name+'">' + r.message.name+ '</a>']));
						}
						d.hide();
						me.frm.reload_doc();
					}
				});
			},
			primary_action_label: __('Create')
		});
		d.show();
	},

	make_delivery_note_based_on_delivery_date: function() {
		var me = this;

		var delivery_dates = [];
		$.each(this.frm.doc.items || [], function(i, d) {
			if(!delivery_dates.includes(d.delivery_date)) {
				delivery_dates.push(d.delivery_date);
			}
		});

		var item_grid = this.frm.fields_dict["items"].grid;
		if(!item_grid.get_selected().length && delivery_dates.length > 1) {
			var dialog = new frappe.ui.Dialog({
				title: __("Select Items based on Delivery Date"),
				fields: [{fieldtype: "HTML", fieldname: "dates_html"}]
			});

			var html = $(`
				<div style="border: 1px solid #d1d8dd">
					<div class="list-item list-item--head">
						<div class="list-item__content list-item__content--flex-2">
							${__('Delivery Date')}
						</div>
					</div>
					${delivery_dates.map(date => `
						<div class="list-item">
							<div class="list-item__content list-item__content--flex-2">
								<label>
								<input type="checkbox" data-date="${date}" checked="checked"/>
								${frappe.datetime.str_to_user(date)}
								</label>
							</div>
						</div>
					`).join("")}
				</div>
			`);

			var wrapper = dialog.fields_dict.dates_html.$wrapper;
			wrapper.html(html);

			dialog.set_primary_action(__("Select"), function() {
				var dates = wrapper.find('input[type=checkbox]:checked')
					.map((i, el) => $(el).attr('data-date')).toArray();

				if(!dates) return;

				$.each(dates, function(i, d) {
					$.each(item_grid.grid_rows || [], function(j, row) {
						if(row.doc.delivery_date == d) {
							row.doc.__checked = 1;
						}
					});
				})
				me.make_delivery_note();
				dialog.hide();
			});
			dialog.show();
		} else {
			this.make_delivery_note();
		}
	},

	make_delivery_note: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
			frm: me.frm
		})
	},

	make_sales_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
			frm: this.frm
		})
	},

	make_maintenance_schedule: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_schedule",
			frm: this.frm
		})
	},

	make_project: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_project",
			frm: this.frm
		})
	},

	make_inter_company_order: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_inter_company_purchase_order",
			frm: this.frm
		});
	},

	make_maintenance_visit: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_visit",
			frm: this.frm
		})
	},

	make_purchase_order: function(){
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("For Supplier"),
			fields: [
				{"fieldtype": "Link", "label": __("Supplier"), "fieldname": "supplier", "options":"Supplier",
				 "description": __("Leave the field empty to make purchase orders for all suppliers"),
					"get_query": function () {
						return {
							query:"erpnext.selling.doctype.sales_order.sales_order.get_supplier",
							filters: {'parent': me.frm.doc.name}
						}
					}},
					{fieldname: 'items_for_po', fieldtype: 'Table', label: 'Select Items',
					fields: [
						{
							fieldtype:'Data',
							fieldname:'item_code',
							label: __('Item'),
							read_only:1,
							in_list_view:1
						},
						{
							fieldtype:'Data',
							fieldname:'item_name',
							label: __('Item name'),
							read_only:1,
							in_list_view:1
						},
						{
							fieldtype:'Float',
							fieldname:'qty',
							label: __('Quantity'),
							read_only: 1,
							in_list_view:1
						},
						{
							fieldtype:'Link',
							read_only:1,
							fieldname:'uom',
							label: __('UOM'),
							in_list_view:1
						}
					],
					data: cur_frm.doc.items,
					get_data: function() {
						return cur_frm.doc.items
					}
				},

				{"fieldtype": "Button", "label": __('Create Purchase Order'), "fieldname": "make_purchase_order", "cssClass": "btn-primary"},
			]
		});

		dialog.fields_dict.make_purchase_order.$input.click(function() {
			var args = dialog.get_values();
			let selected_items = dialog.fields_dict.items_for_po.grid.get_selected_children()
			if(selected_items.length == 0) {
				frappe.throw({message: 'Please select Item form Table', title: __('Message'), indicator:'blue'})
			}
			let selected_items_list = []
			for(let i in selected_items){
				selected_items_list.push(selected_items[i].item_code)
			}
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "erpnext.selling.doctype.sales_order.sales_order.make_purchase_order",
				args: {
					"source_name": me.frm.doc.name,
					"for_supplier": args.supplier,
					"selected_items": selected_items_list
				},
				freeze: true,
				callback: function(r) {
					if(!r.exc) {
						// var args = dialog.get_values();
						if (args.supplier){
							var doc = frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
						else{
							frappe.route_options = {
								"sales_order": me.frm.doc.name
							}
							frappe.set_route("List", "Purchase Order");
						}
					}
				}
			})
		});
		dialog.get_field("items_for_po").grid.only_sortable()
		dialog.get_field("items_for_po").refresh()
		dialog.show();
	},
	hold_sales_order: function(){
		var me = this;
		var d = new frappe.ui.Dialog({
			title: __('Reason for Hold'),
			fields: [
				{
					"fieldname": "reason_for_hold",
					"fieldtype": "Text",
					"reqd": 1,
				}
			],
			primary_action: function() {
				var data = d.get_values();
				frappe.call({
					method: "frappe.desk.form.utils.add_comment",
					args: {
						reference_doctype: me.frm.doctype,
						reference_name: me.frm.docname,
						content: __('Reason for hold: ')+data.reason_for_hold,
						comment_email: frappe.session.user
					},
					callback: function(r) {
						if(!r.exc) {
							me.update_status('Hold', 'On Hold')
							d.hide();
						}
					}
				});
			}
		});
		d.show();
	},
	close_sales_order: function(frm){
		if(cur_frm.doc.reason_ == null || cur_frm.doc.reason_ == "" ){
			cur_frm.set_df_property('reason_', 'reqd', 1);
			frappe.throw("Mention a Reason to close sales order	");
		}
		// frappe.throw("Type Reason to Close this sales order")
		this.frm.cscript.update_status("Close", "Closed")
		// var me = this;
		// frappe.call({
		// 	method: "eie.api.validate_material_request",
		// 	args:{
		// 		"sales_order": this.frm.doc.name,
		// 	},
		// 	callback: function(r){
		// 			//frappe.throw(r.message);
		// 				if (r.message)
		// 				{
		// 					frappe.throw("Cancel Material Request of this Sales Order")
		// 				}
		// 				else{
		// 					me.update_status("Close", "Closed")
		// 				}
		// 		}
		// })
	},
	update_status: function(label, status){
		var doc = this.frm.doc;
		var me = this;
		frappe.ui.form.is_saving = true;
		frappe.call({
			method: "erpnext.selling.doctype.sales_order.sales_order.update_status",
			args: {status: status, name: doc.name},
			callback: function(r){
				me.frm.reload_doc();
			},
			always: function() {
				frappe.ui.form.is_saving = false;
			}
		});
	},
	
});
$.extend(cur_frm.cscript, new erpnext.selling.SalesOrderController({frm: cur_frm}));

frappe.ui.form.on("Sales Order", {
    cost_center:function(frm){
        if(frm.doc.cost_center){
            frm.doc.items.forEach(d => {
                frappe.model.set_value(d.doctype, d.name, 'cost_center', frm.doc.cost_center);
            });
        }
    }
});

