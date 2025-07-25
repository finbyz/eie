import frappe
from frappe import _



def before_insert(self,method):
    if self.message_id:
        existing_communication = frappe.db.exists(
            "Communication",
            {
                "message_id": self.message_id
            }
        )
        if existing_communication:
            frappe.throw(_("A communication with this message ID already exists for the specified reference."))