# -*- coding: utf-8 -*-
# Copyright (c) 2018, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
# from erpnext.accounts.general_ledger import delete_gl_entries
from frappe.utils.background_jobs import enqueue

class Cities(Document):
	def update_gl_entries(self):
		# enqueue(_update_gl_entries, queue='long', timeout=4000, job_name="Updating GL Entries", self=self)

		self._update_gl_entries()

	def _update_gl_entries(self):
		gl_patch_list = self.gl_entry_patch.split("\n")

		cnt = 0
		for document in gl_patch_list[:10]:
			doctype, docname = document.split(":")

			# if frappe.db.exists(doctype, docname):
			try:
				doc = frappe.get_doc(doctype, docname)
				if doc.docstatus == 1:
					delete_gl_entries(voucher_type=doc.doctype, voucher_no=doc.name)
					doc.make_gl_entries(repost_future_gle=False)

					self.success = str(self.success) + document + "\n"
					cnt += 1
					frappe.publish_realtime(event="cities_progress", message={'status': str(cnt), 'customer': doctype, 'invoice': docname}, user=frappe.session.user)

			except Exception as e:
				frappe.publish_realtime(event="cities_progress", message={'status': "Error", 'customer': doctype, 'invoice': docname}, user=frappe.session.user)

		frappe.msgprint("GL Entries Updated")
		self.save()

def delete_gl_entries(voucher_type=None, voucher_no=None):
	frappe.db.sql("""delete from `tabGL Entry` where voucher_type=%s and voucher_no=%s""",
		(voucher_type, voucher_no))
