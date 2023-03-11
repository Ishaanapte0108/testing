# Copyright (c) 2023, credence analytics and contributors
# For license information, please see license.txt

import frappe, datetime, re, pandas as pd
from frappe.model.document import Document
from frappe.utils.data import end

doctype = 'Employee Attrition'

class EmployeeAttrition(Document):
		
		def autoname(self):
			prefix = f'EA_{self.reporting_date}_{self.department if self.department else self.level}'
			self.name = prefix

		def before_save(self):			
			
			self.attrition_number = self.employee_leaving - self.correction
			try:
				b = self.period_begin_team_size
				c = self.period_end_team_size
				self.attrition_percent = (self.attrition_number / ((b+c)/2))*100
			except Exception as e:				
				frappe.throw(e)

		def validate(self):
			
			#validate if reporting date is quater end date only
			[year,month,date] = self.reporting_date.split('-')
			input_date = datetime.date(int(year),int(month),int(date))
			quater_end_date = get_month_end(input_date)
			if input_date != quater_end_date:
				frappe.throw('The date is not a qauter end date')

			#validate the team begin size
			if self.period_begin_team_size < 0:
				frappe.throw('Team size at the beginning cannot be less than 0')
			
			#validate the team end size
			if self.period_end_team_size < 0:
				frappe.throw('Team size at the end cannot be less than 0')
			
			#validate employee leaving
			if self.employee_leaving < 0:
				frappe.throw('Employee leaving number cannot be less than 0')
			
			#validate employee leaving
			
			if self.correction < 0:
				frappe.throw('Correction value cannot be less than 0')

			if self.correction > self.employee_leaving:
				frappe.throw('Correction value cannot be greater than the number of employees leaving')
			
			# validate if same record exists in database
			existing_record = frappe.db.exists('Employee Attrition', {'name': self.name})
			if existing_record and existing_record != self.name:
				frappe.throw('There already exists such a record in the database')


@frappe.whitelist()
def getEmployeeAttrition(reporting_date):
		
		def dataEntry(row):
			
			#insert new document into database
			doc = frappe.new_doc(doctype=doctype)
			#assign appropriate values
			doc.level, doc.department = ('Company', None) if row['Department'] == 'Company' else ('Department', row['Department'])
			doc.reporting_date = reporting_date
			doc.period_begin_team_size = row['Period Begin Team Size']
			doc.period_end_team_size = row['Period End Team Size']
			doc.employee_leaving = row['Employee Leaving']
			flag = False
			try:
				#obtain the docname for the document we wish to save and check if it exists in the database
				docname = f"EA_{reporting_date}_{row['Department']}"
				if frappe.get_doc(doctype, docname):
					flag = True
			except frappe.DoesNotExistError:
				frappe.message_log.pop()
	
			if flag:	
				#if it exists in the database then update it, if any changes and return inorder to compute for the next row
				doc1 = frappe.get_doc(doctype, docname)
				doc1.level, doc1.department = ('Company', None) if row['Department'] == 'Company' else ('Department', row['Department'])
				doc1.reporting_date = reporting_date
				doc1.period_begin_team_size = row['Period Begin Team Size']
				doc1.period_end_team_size = row['Period End Team Size']
				doc1.employee_leaving = row['Employee Leaving']							
				doc1.save()
				return						

			#if it does not exist then insert it into the database				
			doc.insert(ignore_permissions=True)
			frappe.db.commit()
				
		#check if date in quater end date
		dates = reporting_date.split('-')
		refined = list(map(lambda x: int(re.sub("^0+(?!$)", '', x)),dates))
		a = pd.Timestamp(refined[0], refined[1], refined[2])
		
		if a.is_quarter_end:

			# get previous quater end date
			begin_date = a - pd.offsets.QuarterEnd()
			begin_date = begin_date.strftime("%Y-%m-%d")
			#get period begin team size, period end team size and employee leaving count from the `tabEmployee` table
			data = frappe.db.sql(f"SELECT department,COUNT(CASE WHEN status = 'active' and date_of_joining <='{begin_date}' THEN 1 ELSE NULL END) AS 'Period Begin Team Size',COUNT(CASE WHEN status = 'active' and date_of_joining <='{reporting_date}' THEN 1 ELSE NULL END) AS 'Period End Team Size',COUNT(CASE WHEN status = 'left' and relieving_date > '{begin_date}' and relieving_date <= '{reporting_date}' THEN 1 ELSE NULL END) AS 'Employees Leaving' FROM `tabEmployee` GROUP BY department;")
			#put receieved data into pandas dataframe for further processing
			df = pd.DataFrame(data, columns=['Department', 'Period Begin Team Size', 'Period End Team Size', 'Employee Leaving'])
			#calculate the total period begin team size, period end team size and employee leaving count for the entire company
			company_row = pd.DataFrame(df.sum(axis = 0), columns=['Company']).T
			company_row['Department'] = 'Company'
			df = df.append(company_row, ignore_index = True)
			#apply dataEntry function for each row, to enter values in the database appropriately
			df.apply(dataEntry, axis = 1)

			return 'Success'
		
		else:
			frappe.throw('Please enter a quater end date')
