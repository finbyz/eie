// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

erpnext.SMSManager = function SMSManager(doc) {
	var me = this;

	this.setup = function() {
		
		var default_msg = {
			'Lead'				: '',
			'Opportunity'		: 'Your enquiry has been logged into the system. Ref No: ' + doc.name +'Contact',
			'Quotation'			: 'Quotation No. ' + doc.name + ` has been sent via email. Please check and confirm. Thanks!.\nContact\nEIEIPL`,
			'Sales Order'		: 'Sales Order No. ' + doc.name + ' has been created against your PO :'+ doc.po_no +" "+ ` Please check and confirm.\nContact\nEIEIPL`,

			'Delivery Note'		: 'Items has been delivered against delivery note: ' + doc.name + (doc.po_no ? (' for your PO: ' + doc.po_no) : '')+`\nContact`,

			'Sales Invoice': 'Goods against your PO No' +doc.po_no + ` has been dispatched. Please check your mail for details and confirm the receipt in due course.\nContact\nEIEIPL`,

			'Material Request' : 'Material Request ' + doc.name + ` has been raised in the system.\nContact\nEIEIPL`,
	

			'Purchase Order'	: doc.name + ` has been sent via email . Please check and confirm the order.\nContact\nEIEIPL`,
			'Purchase Receipt'	: 'Items has been received against purchase receipt: ' + doc.name +`\nContact\nEIEIPL`,
			'Payment Entry' : "Payment of Rs."+' '+ doc.paid_amount +' '+ `released against your Invoice. Please confirm when received.\nContact\nEIEIPL`
		}

		if (in_list(['Sales Order', 'Delivery Note', 'Sales Invoice'], doc.doctype))
		frappe.model.get_value('User', frappe.session.user , 'phone' ,(r)=>{
			let text = default_msg[doc.doctype].replace("Contact", r.phone)
			this.show(doc.contact_person, 'Customer', doc.customer, '', text);
		})
			
		else if (doc.doctype === 'Quotation')
		frappe.model.get_value('User', frappe.session.user , 'phone' ,(r)=>{
			let text = default_msg[doc.doctype].replace("Contact", r.phone)
			this.show(doc.contact_person, 'Customer', doc.party_name, '', text);
		})
			
		
		else if (in_list(['Purchase Order', 'Purchase Receipt'], doc.doctype))
		frappe.model.get_value('User', frappe.session.user , 'phone' ,(r)=>{
			let text = default_msg[doc.doctype].replace("Contact", r.phone)
			this.show(doc.contact_person, 'Supplier', doc.supplier, '', text);
		})
			
		else if (doc.doctype == 'Lead')
		frappe.model.get_value('User', frappe.session.user , 'phone' ,(r)=>{
			let text = default_msg[doc.doctype].replace("Contact", r.phone)
			this.show('', '', '', doc.mobile_no, text);
		})
			
		else if (doc.doctype == 'Opportunity')
		frappe.model.get_value('User', frappe.session.user , 'phone' ,(r)=>{
			let text = default_msg[doc.doctype].replace("Contact", r.phone)
			this.show('', '', '', doc.contact_no, text);
		})
			
		else if (doc.doctype == 'Material Request')
		frappe.model.get_value('User', frappe.session.user , 'phone' ,(r)=>{
			let text = default_msg[doc.doctype].replace("Contact", r.phone)
			this.show('', '', '', '', text);
		})
		else if (doc.doctype == 'Payment Entry')
		frappe.model.get_value('User', frappe.session.user , 'phone' ,(r)=>{
			let text = default_msg[doc.doctype].replace("Contact", r.phone)
			this.show(doc.contact_person, doc.party_type ,doc.party , '', text);
			})
			
		

	};

	this.get_contact_number = function (contact, ref_doctype, ref_name) {
		frappe.call({
			method: "frappe.core.doctype.sms_settings.sms_settings.get_contact_number",
			args: {
				contact_name: contact,
				ref_doctype: ref_doctype,
				ref_name: ref_name
			},
			callback: function(r) {
				if (r.exc) { frappe.msgprint(r.exc); return; }
				
				me.number = r.message;
				me.show_dialog();
			}
		});
	};

	this.show = function(contact, ref_doctype, ref_name, mobile_nos, message) {
		this.message = message;
		if (mobile_nos) {
			me.number = mobile_nos;
			me.show_dialog();
		} else if (contact){
			this.get_contact_number(contact, ref_doctype, ref_name)
		} else {
			me.show_dialog();
		}
	}
	this.show_dialog = function() {
		if(!me.dialog)
			me.make_dialog();
		me.dialog.set_values({
			'message': me.message,
			'number': me.number
		})
		me.dialog.show();
	}
	this.make_dialog = function() {
		var d = new frappe.ui.Dialog({
			title: 'Send SMS',
			width: 400,
			fields: [
				{fieldname:'number', fieldtype:'Data', label:'Mobile Number', reqd:1},
				{fieldname:'message', fieldtype:'Text', label:'Message', reqd:1},
				{fieldname:'send', fieldtype:'Button', label:'Send'}
			]
		})
		d.fields_dict.send.input.onclick = function() {
			var btn = d.fields_dict.send.input;
			var v = me.dialog.get_values();
			if(v) {
				$(btn).set_working();
				frappe.call({
					method: "frappe.core.doctype.sms_settings.sms_settings.send_sms",
					args: {
						receiver_list: [v.number],
						msg: v.message
					},
					callback: function(r) {
						$(btn).done_working();
						if(r.exc) {frappe.msgprint(r.exc); return; }
						me.dialog.hide();
					}
				});
			}
		}
		this.dialog = d;
	}
	this.setup();
}
