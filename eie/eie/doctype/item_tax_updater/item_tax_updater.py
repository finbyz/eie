# -*- coding: utf-8 -*-
# Copyright (c) 2018, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import db, msgprint, _

class ItemTaxUpdater(Document):
	def get_items(self):
		
		items = [self.item_group]
		loop = False
		is_group = frappe.db.get_value("Item Group", self.item_group, "is_group")
		
		if is_group:
			loop = True
		
		group = [self.item_group]
		while loop:
			item_group = []
			for d in group:
				item_list = frappe.db.get_values('Item Group',{"parent_item_group": d}, ["item_group_name", "is_group"], as_dict=1)
				
				for item in item_list:
					items.append(item["item_group_name"])
					if item["is_group"]:
						item_group.append(item["item_group_name"])
			
			if item_group:
				group = item_group
			else:
				loop = False
			
		self.set("item_group_item", [])
		for i in items:
			res = frappe.db.sql("""
			select 
				item_code
			from
				`tabItem`
			where
				item_group='%s'""" % i)
				
			for row in res:
				self.append("item_group_item",{
					"item_group_name" : i,
					"item_code" : row[0]
				})
		return