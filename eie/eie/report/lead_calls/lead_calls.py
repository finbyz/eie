# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _, msgprint
from frappe.utils import getdate, nowdate, date_diff

def execute(filters=None):
	filters.from_date = getdate(filters.from_date or nowdate())
	filters.to_date = getdate(filters.to_date or nowdate())
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	return columns, data , None, chart

	
def get_columns():
	columns = [_("Lead") + ":Link/Lead:80",  
				_("User") + ":Link/User:100",  
				_("Date") + ":Date:120",
				_("Caller") + "::110", 
				_("Organization") + "::180", 
				_("Person") + "::120", 
				_("Comment") + ":data:400",  
				_("Schedule") + ":Date:120",  
				_("Source") + "::100", 
				_("Status") + "::100", 
				_("Mobile") + "::100", 
				_("Phone") + "::100"
	]
	return columns

def get_data(filters):

	where_clause = ''
	where_clause+=filters.user and " and co.user = '%s' " % filters.user or ""	
	where_clause+=filters.lead and " and co.reference_name = '%s' " % filters.lead or ""
	
	where_clause += " and co.communication_date between '%s 00:00:00' and '%s 23:59:59' " % (filters.from_date, filters.to_date)
	
	return frappe.db.sql("""
		select
			co.reference_name as "Lead", co.user as "User" , co.communication_date as "Date", co.sender_full_name as "Caller", ld.company_name as "Organization", ld.lead_name as "Person",  co.subject as "Comment", ld.contact_date as "Schedule", ld.source as "Source" , ld.Status as "Status" , ld.mobile_no as "Mobile" ,	ld.phone as "Phone"
		from
			`tabCommunication` as co left join `tabLead` as ld on (co.reference_name = ld.name)
		where
			co.reference_doctype = "Lead" and co.comment_type="Comment"
			%s
		order by
			co.communication_date desc"""%where_clause, as_dict=1)
			
def get_chart_data(data, filters):
	count = []
	based_on, date_range = None, None
	period = {"Day": "%d", "Week": "%W", "Month": "%m"}
	from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)
	labels = list()
	diff = date_diff(filters.to_date, filters.from_date)
	
	if diff <= 30:
		based_on = "Day"
		date_range = diff
	elif diff <= 90 and diff > 30:
		based_on = "Week"
		date_range = int(to_date.strftime(period[based_on])) - int(from_date.strftime(period[based_on]))
	elif diff > 90:
		based_on = "Month"
		date_range = int(to_date.strftime(period[based_on])) - int(from_date.strftime(period[based_on]))
		
	if based_on == "Day":
		for d in xrange(date_range+1):
			cnt = 0
			date = from_date + datetime.timedelta(days=d)
			for row in data:
				sql_date = getdate(row["Date"])
				if date == sql_date:
					cnt += 1
			
			count.append(cnt)
			labels.append(date.strftime("%d-%b '%y"))
	
	else:
		period_date = dict()
		for x in xrange(date_diff(to_date, from_date)+1):
			tmp_date = from_date + datetime.timedelta(days=x)
			tmp_period = str(tmp_date.strftime(period[based_on]))
			if tmp_period not in period_date:
				period_date[tmp_period] = [tmp_date]
			else:
				period_date[tmp_period].append(tmp_date)
		
		for key, values in sorted(period_date.items()):
			cnt = 0
			for date in values:
				for row in data:
					sql_date = getdate(row["Date"])
					if date == sql_date:
						cnt += 1
						
			count.append(cnt)
			labels.append(values[0].strftime("%d-%b") + " to " + values[-1].strftime("%d-%b"))
	
	datasets = []
	
	if count:
		datasets.append({
			'title': "Total",
			'values': count
		})
	
	chart = {
		"data": {
			'labels': labels,
			'datasets': datasets
		}
	}
	chart["type"] = "bar"
	return chart