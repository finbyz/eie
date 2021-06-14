from __future__ import unicode_literals
from frappe import _


def get_data(data):
	data['fieldname']= 'material_request'
	data['transactions']= [
		{
			'label': _('Related'),
			'items': ['Request for Quotation', 'Supplier Quotation', 'Purchase Order', 'Stock Entry', 'Pick List']
		},
		{
			'label': _('Manufacturing'),
			'items': ['Work Order','Production Plan'] # finbyz change add production plan in dashboard
		}
	]
	return data