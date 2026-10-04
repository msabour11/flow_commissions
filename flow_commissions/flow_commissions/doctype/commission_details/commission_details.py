# Copyright (c) 2026, Mohamed AbdElsabour and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CommissionDetails(Document):
	def fetch_commission(self):
		from flow_commissions.flow_commissions.doctype.commission_rule_settings.commission_rule_settings import (
			calculate_commission,
		)

		if not self.parent or not self.from_date or not self.to_date:
			return

		res = calculate_commission(self.parent, self.from_date, self.to_date)
		self.total_qty = res.get("total_qty", 0.0)
		self.qty = res.get("total_qty", 0.0)
		self.commission_amount = res.get("commission_amount", 0.0)
