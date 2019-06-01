# -*- coding: utf-8 -*-
# Copyright (c) 2017, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe import msgprint, db, _
from frappe.core.doctype.communication.email import make
from frappe.utils import get_datetime

class MeetingSchedule(Document):		
	def send_invitation_message(self):
		if not self.contact_email:
			msgprint(_("Please enter email id"))
			return
		
		subject = "Scheduled Meeting on %s " % get_datetime(self.scheduled_from).strftime("%A %d-%b-%Y")
		
		r = make(recipients=self.contact_email,
			subject=subject, 
			content=self.invitation_message,
			sender=frappe.session.user,
			doctype=self.doctype, 
			name=self.name,
			send_email=True)
		
		msgprint(_("Mail sent successfully"))
	
@frappe.whitelist()
def make_meeting(source_name, target_doc=None):	
	doclist = get_mapped_doc("Meeting Schedule", source_name, {
			"Meeting Schedule":{
				"doctype": "Meetings",
				"field_map": {
					"name": "schedule_ref",
					"scheduled_from": "meeting_from",
					"scheduled_to": "meeting_to"
				}
			}
	}, target_doc)	
	return doclist
	
@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.
	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	filters = json.loads(filters)
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Meeting Schedule", filters)

	return frappe.db.sql("""
			select 
				name, scheduled_from, scheduled_to, organisation
			from 
				`tabMeeting Schedule`
			where
				(scheduled_from <= %(end)s and scheduled_to >= %(start)s) {conditions}
			""".format(conditions=conditions),
				{
					"start": start,
					"end": end
				}, as_dict=True, update={"allDay": 0})