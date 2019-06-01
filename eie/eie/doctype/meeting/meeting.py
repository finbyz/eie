# -*- coding: utf-8 -*-
# Copyright (c) 2018, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime
from frappe import msgprint, db, _
import json
import datetime
from frappe.core.doctype.communication.email import make

class Meeting(Document):
	pass





@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.
	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	filters = json.loads(filters)
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Meeting", filters)

	return frappe.db.sql("""
			select 
				name, meeting_from, meeting_to, organisation
			from
				`tabMeeting`
			where
				(meeting_from <= %(end)s and meeting_to >= %(start)s) {conditions}
			""".format(conditions=conditions),
				{
					"start": start,
					"end": end
				}, as_dict=True, update={"allDay": 0})

@frappe.whitelist()	
def send_meetingmail(doc_name):
	doc = frappe.get_doc("Meeting", doc_name)
	context = {"doc": doc}	
	
	minutes_message = """<p>Greeting from EIE Instruments Pvt. Ltd.!!</p>
				<p>Thank you for sparing your valuable time.
				These are the points that were covered in meeting:</p><br>"""
				
	minutes_message += frappe.render_template(doc.discussion, context)
	
	if doc.actionables:
		actionable_heading = """<br><p>
							<strong>Actionables</strong>
						</p>
						<table border="1" cellspacing="0" cellpadding="0">
							<tbody>
								<tr>
									<td width="45%" valign="top">
										<p>
											<strong>Actionable</strong>
										</p>
									</td>
									<td width="30%" valign="top">
										<p>
											<strong>Responsibility</strong>
										</p>
									</td>
									<td width="25%" valign="top">
										<p>
											<strong>Exp. Completion Date</strong>
										</p>
									</td>
								</tr>"""
								
		actionable_row = """<tr>
								<td width="45%" valign="top"> {0}
								</td>
								<td width="30%" valign="top"> {1}
								</td>
								<td width="25%" valign="top"> {2}
								</td>
							</tr>"""
		
		actionable_rows = ""
		for row in doc.actionables:
			actionable_rows += actionable_row.format(row.actionable, row.responsible, row.get_formatted('expected_completion_date'))
			
		actionable_heading += actionable_rows
		actionable_heading += "</tbody></table>"
		minutes_message += actionable_heading
	
	subject = "Minutes of the Meeting on Date - {0}".format(get_datetime(doc.meeting_from).strftime("%A %d-%b-%Y"))
	
	representatives = [row.employee_user_id for row in doc.eie_representatives]

	if len(doc.customer_representatives) == 0:
		representatives.append(doc.contact_email)

	elif len(doc.customer_representatives) > 0:
		emails = [li.email_id for li in doc.customer_representatives]
		frappe.errprint(emails)
		for i in emails:
			representatives.append(i)
			
	
	recipients = ",".join(representatives)
	
	# Send mail to representatives
	
	r = make(recipients=recipients, 
		#cc="deepak@eieinstruments.com",
		subject=subject, 
		content=minutes_message,
		sender=frappe.session.user,
		sender_full_name=frappe.db.get_value("Employee",{"user_id":frappe.session.user},"employee_name"),
		doctype=doc.doctype,
		name=doc.name,
		send_email=True)

	frappe.msgprint(_("Minutes of the Meeting sent to All Participants"))