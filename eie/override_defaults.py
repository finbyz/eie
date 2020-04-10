import frappe
from frappe.social.doctype.energy_point_log.energy_point_log import get_alert_dict

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
