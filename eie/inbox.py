from __future__ import unicode_literals
import frappe
import json

@frappe.whitelist()
def create_email_flag_queue(names, action):
	""" create email flag queue to mark email either as read or unread """
	def mark_as_seen_unseen(name, action):
		doc = frappe.get_doc("Communication", name)
		if action == "Read":
			doc.add_seen()
		else:
			_seen = json.loads(doc._seen or '[]')
			_seen = [user for user in _seen if frappe.session.user != user]
			doc.db_set('_seen', json.dumps(_seen), update_modified=False)

	if not all([names, action]):
		return

	for name in json.loads(names or []):
		uid, seen_status, email_account = frappe.db.get_value("Communication", name, 
			["ifnull(uid, -2)", "ifnull(seen, 0)", "email_account"])

		# can not mark email SEEN or UNSEEN without uid
		if not uid or uid == -2:
			continue

		seen = 1 if action == "Read" else 0
		# check if states are correct
		if (action =='Read' and seen_status == 0) or (action =='Unread' and seen_status == 1):
			create_new = True
			email_flag_queue = frappe.db.sql("""select name, action from `tabEmail Flag Queue`
				where communication = %(name)s and is_completed=0""", {"name":name}, as_dict=True)

			for queue in email_flag_queue:
				if queue.action != action:
					frappe.delete_doc("Email Flag Queue", queue.name, ignore_permissions=True)
				elif queue.action == action:
					# Read or Unread request for email is already available
					create_new = False

			if create_new:
				flag_queue = frappe.get_doc({
					"uid": uid,
					"action": action,
					"communication": name,
					"doctype": "Email Flag Queue",
					"email_account": email_account
				})
				flag_queue.save(ignore_permissions=True)
				frappe.db.set_value("Communication", name, "seen", seen, 
					update_modified=False)
				mark_as_seen_unseen(name, action)

@frappe.whitelist()
def change_email_queue_status():
	pass
	# from frappe.email.doctype.email_queue.email_queue import retry_sending
	# from frappe.email.queue import send_one

	# eqs = frappe.get_list("Email Queue", filters={'status': "Sending"})

	# if eqs:
	# 	for d in eqs:
	# 		# retry_sending(d.name)
	# 		# send_one(d.name, now=True)
	# 		doc = frappe.get_doc("Email Queue", d.name)
	# 		doc.status = "Not Sent"
	# 		doc.save(ignore_permissions=True)
	# 		send_one(doc.name, now=True)
	# 	else:
	# 		frappe.db.commit()
