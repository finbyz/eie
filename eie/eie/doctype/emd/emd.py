# -*- coding: utf-8 -*-
# Copyright (c) 2018, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt


class EMD(Document):
	
	def on_submit(self):
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = self.posting_date
		jv.voucher_type = "EMD Entry"
		jv.company = self.company
		
		abbr = frappe.db.get_value("Company",self.company,'abbr')
		
		if jv.company == "EIE Instruments Pvt. Ltd." :
			jv.naming_series = "EPL/EMDJV/"
		else:
			jv.naming_series = "VPL/EMDJV/"
		jv.cheque_no = self.reference_num
		jv.cheque_date = self.reference_date
		

		jv.append('accounts',{
			'account':self.deposit_account,
			'party_type':'Customer',
			'party':self.customer,
			'debit_in_account_currency':self.amount,
			'cost_center':'Main - ' + abbr
		})


		if self.expense_account:

			jv.append('accounts' ,{
			'account': self.expense_account,
			'debit_in_account_currency':self.extra_charges,
			'cost_center':'Main - ' + abbr
		})

		
		if self.is_opening == "Yes":
			jv.append('accounts',{
				'account':"Temporary Opening - " + abbr ,
				'credit_in_account_currency':flt(self.amount),
				'cost_center':'Main - ' + abbr
			})
			jv.is_opening = "Yes"
		else:
			jv.append('accounts',{
				'account':self.bank_account ,
				'credit_in_account_currency':flt(self.amount+self.extra_charges),
				'cost_center':'Main - ' + abbr
			})

		

		jv.save()
		self.db_set('journal_entry' , jv.name)
		jv.submit()

	def cancel_return(self):
		if self.return_journal_entry:
			jv = frappe.get_doc("Journal Entry" , self.return_journal_entry)
			self.returned = 0
			self.return_account = ''
			self.return_date = ''
			self.db_set('return_journal_entry','')
			jv.cancel()
		
	def on_update_after_submit(self):
		if self.returned == 1 and not self.return_journal_entry:
			jv = frappe.new_doc("Journal Entry")
			jv.posting_date = self.return_date
			jv.voucher_type = "EMD Entry"
			jv.company = self.company
			
			abbr = frappe.db.get_value("Company",self.company,'abbr')
			
			if jv.company == "EIE Instruments Pvt. Ltd." :
				jv.naming_series = "EPL/EMDJV/"
			else:
				jv.naming_series = "VPL/EMDJV/"
			jv.cheque_no = self.reference_num
			jv.cheque_date = self.reference_date
			
			jv.append('accounts',{
				'account':self.deposit_account,
				'party_type':'Customer',
				'party':self.customer,
				'credit_in_account_currency':self.amount,
				'cost_center':'Main - ' + abbr
			})

			if self.interest_account and self.interest_amount > 0:

				jv.append('accounts' ,{
				'account': self.interest_account,
				'credit_in_account_currency':self.interest_amount,
				'cost_center':'Main - ' + abbr		
				})


				jv.append('accounts',{
					'account':self.return_account ,
					'debit_in_account_currency':flt(self.amount+self.interest_amount),
					'cost_center':'Main - ' + abbr
				})
			else:
				jv.append('accounts',{
					'account':self.return_account ,
					'debit_in_account_currency':flt(self.amount),
					'cost_center':'Main - ' + abbr
				})
			
			jv.save()
			self.db_set('return_journal_entry' , jv.name)
			jv.submit()

	def on_cancel(self):
		se = frappe.get_doc("Journal Entry",self.journal_entry)
		if self.get("return_journal_entry"):
			se1 = frappe.get_doc("Journal Entry",self.return_journal_entry)
			se1.cancel()
			self.db_set('return_journal_entry','')

		se.cancel()
		self.db_set('journal_entry','')
		

