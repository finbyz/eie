# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "eie"
app_title = "EIE"
app_publisher = "FinByz Tech Pvt. Ltd."
app_description = "Custom App for EIE"
app_icon = "octicon octicon-circuit-board"
app_color = "orange"
app_email = "info@finbyz.com"
app_license = "GPL 3"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/eie/css/eie.css"

app_include_css = [
	"/assets/eie/css/eie.min.css",
	"assets/css/summernote.min.css"
]
app_include_js = [
	"/assets/eie/js/eie.min.js",
	"assets/js/summernote.min.js",
	"assets/js/comment_desk.min.js",
	"assets/js/editor.min.js",
	"assets/js/timeline.min.js"
]
# include js, css files in header of web template
# web_include_css = "/assets/eie/css/eie.css"
# web_include_js = "/assets/eie/js/eie.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}
page_js = {"permission-manager" : "public/js/eie.min.js"}

# include js in doctype views
#doctype_js = {"User" : "public/js/user.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "eie.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "eie.install.before_install"
# after_install = "eie.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "eie.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"eie.tasks.all"
# 	],
# 	"daily": [
# 		"eie.tasks.daily"
# 	],
# 	"hourly": [
# 		"eie.tasks.hourly"
# 	],
# 	"weekly": [
# 		"eie.tasks.weekly"
# 	]
# 	"monthly": [
# 		"eie.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "eie.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "eie.event.get_events"
# }
# override_whitelisted_methods = {
#  	"erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice": "eie.api.make_sales_invoice",
#  	"frappe.core.page.permission_manager.permission_manager.get_roles_and_doctypes": "eie.permission.get_roles_and_doctypes",
#  	"frappe.core.page.permission_manager.permission_manager.get_permissions": "eie.permission.get_permissions",
# 	"frappe.core.page.permission_manager.permission_manager.add": "eie.permission.add",
# 	"frappe.core.page.permission_manager.permission_manager.update": "eie.permission.update",
# 	"frappe.core.page.permission_manager.permission_manager.remove": "eie.permission.remove",
# 	"frappe.core.page.permission_manager.permission_manager.reset": "eie.permission.reset",
# 	"frappe.core.page.permission_manager.permission_manager.get_users_with_role": "eie.permission.get_users_with_role",
# 	"frappe.core.page.permission_manager.permission_manager.get_standard_permissions": "eie.permission.get_standard_permissions",
# 	#"erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding_reference_documents": "eie.pe_override.get_outstanding_reference_documents",
# 	#"frappe.email.inbox.create_email_flag_queue": "eie.inbox.create_email_flag_queue",
# }



doc_events = {
	"Sales Invoice": {
		"validate": "eie.api.si_validate",
		"before_save": "eie.api.si_before_save",
		"on_submit": "eie.api.si_on_submit",
		"on_cancel": "eie.api.si_on_cancel",
	},
	# "Payment Entry": {
		# "validate" : "eie.api.pe_validate",
		# "on_submit": "eie.api.pe_on_submit",
	# },
	"Purchase Order": {
		"before_save": "eie.api.po_before_save",
		"on_submit": "eie.api.po_on_submit",
		"on_cancel": "eie.api.po_on_cancel",
	},
	"Purchase Receipt":{
		"before_save": "eie.api.update_serial_no",
		"before_submit": "eie.api.validate_serial_nos",
	},
	"Purchase Invoice": {
		"before_save": "eie.api.pi_before_save",
	},
	"Packing Slip": {
		"before_save": "eie.api.ps_before_save",
	},
	"Sales Order": {
		"validate": "eie.api.so_validate",
		"before_save": "eie.api.so_before_save",
	},
	"Stock Entry": {
		"before_save": "eie.api.SE_before_save",
		"before_submit": "eie.api.validate_serial_nos",
	},
	"Serial No": {
		"before_save": "eie.api.update_actual_serial_no",
	},
	"Delivery Note": {
		"validate": "eie.api.dn_validate",
		"before_save": "eie.api.dn_before_save",
		"on_submit": "eie.api.dn_on_submit",
		"on_cancel": "eie.api.dn_on_cancel",
	},
	"Item": {
		"before_rename": "eie.api.item_before_rename",
	},
	"Item Price": {
		"before_save": "eie.api.IP_before_save",
	},
	"Quotation": {
		"validate": "eie.api.qt_validate",
		"before_save": "eie.api.qt_before_save",
	},
	"Customer": {
		"before_save": "eie.api.customer_before_save",
	},
	"Material Request": {
		"before_save": "eie.api.mr_before_save",
	},
	("Sales Invoice", "Purchase Invoice", "Payment Request", "Payment Entry", "Journal Entry", "Material Request", "Purchase Order", "Work Order", "Production Plan", "Stock Entry", "Quotation", "Sales Order", "Delivery Note", "Purchase Receipt", "Packing Slip"): {
		"before_naming": "eie.api.docs_before_naming",
	}
}

scheduler_events = {
	# "all": [
	# 	"eie.inbox.change_email_queue_status",
	# ],
	"daily": [
		"eie.api.create_purchase_order_daily",
		"eie.api.sales_invoice_mails",
		"eie.api.calibration_mails_daily",
		"eie.api.emd_sd_mail",
	],
}
import frappe

def override_after_insert(self):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
	alert_dict = get_alert_dict(self)
	if alert_dict:
		frappe.publish_realtime('energy_point_alert', message=alert_dict, user=self.user)

	frappe.cache().hdel('energy_points', self.user)
	frappe.publish_realtime('update_points', after_commit=True)

	if self.type not in ['Review', 'Revert']:
		reference_user = self.user if self.type == 'Auto' else self.owner
		notification_doc = {
			'type': 'Energy Point',
			'document_type': self.reference_doctype,
			'document_name': self.reference_name,
			'subject': get_notification_message(self),
			'from_user': reference_user,
			'email_content': '<div>{}</div>'.format(self.reason) if self.reason else None
		}

		enqueue_create_notification(self.user, notification_doc)
		
def revert(self, reason):
	if self.type != 'Auto':
		frappe.throw(_('This document cannot be reverted'))

	if self.get('reverted'):
		return

	self.reverted = 1
	self.save(ignore_permissions=True)

	revert_log = frappe.get_doc({
		'doctype': 'Energy Point Log',
		'points': -(self.points),
		'type': 'Revert',
		'user': self.user,
		'reason': reason,
		'reference_doctype': self.reference_doctype,
		'reference_name': self.reference_name,
		'revert_of': self.name
	}).insert(ignore_permissions=True)

	return revert_log

from frappe.social.doctype.energy_point_log.energy_point_log import EnergyPointLog, get_alert_dict
# from eie.api import revert
EnergyPointLog.revert = revert
EnergyPointLog.after_insert = override_after_insert
