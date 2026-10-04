# Copyright (c) 2026, Mohamed AbdElsabour and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class CommissionRuleSettings(Document):
	pass


@frappe.whitelist()
def fetch_commission_for_row(sales_person, from_date, to_date):
	"""
	Fetch submitted Sales Invoices for the sales_person between from_date and to_date,
	group by sales_type, and calculate commission_amount according to Commission Rule Settings.
	"""
	if not sales_person:
		frappe.throw(_("Sales Person is required."))
	if not from_date or not to_date:
		frappe.throw(_("Both From Date and To Date are required."))

	from_date = getdate(from_date)
	to_date = getdate(to_date)

	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date."))

	return calculate_commission(sales_person, from_date, to_date)


def calculate_commission(sales_person, from_date, to_date):
	"""
	Core calculation logic for sales person commissions based on sales_type rules.
	"""
	has_direct_sp = frappe.db.has_column("Sales Invoice", "sales_person")

	# Fetch matching submitted invoices
	direct_sp_clause = "OR si.sales_person = %(sales_person)s" if has_direct_sp else ""
	query = f"""
		SELECT
			si.name,
			si.posting_date,
			si.sales_type,
			si.total_qty,
			st.sales_person as team_sales_person,
			COALESCE(st.allocated_percentage, 100.0) as allocated_percentage
		FROM `tabSales Invoice` si
		LEFT JOIN `tabSales Team` st
			ON st.parent = si.name
			AND st.parenttype = 'Sales Invoice'
			AND st.sales_person = %(sales_person)s
		WHERE si.docstatus = 1
		  AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
		  AND (
			  st.sales_person = %(sales_person)s
			  {direct_sp_clause}
		  )
		ORDER BY si.posting_date ASC, si.name ASC
	"""

	invoices = frappe.db.sql(
		query,
		{
			"sales_person": sales_person,
			"from_date": from_date,
			"to_date": to_date,
		},
		as_dict=True,
	)

	# Aggregate quantities by sales_type
	type_qty_map = {}
	total_qty = 0.0
	invoice_details = []

	for inv in invoices:
		pct = flt(inv.allocated_percentage)
		if pct <= 0:
			pct = 100.0

		inv_qty = flt(inv.total_qty)
		if not inv_qty:
			item_sum = frappe.db.sql(
				"SELECT COALESCE(SUM(qty), 0) FROM `tabSales Invoice Item` WHERE parent = %s",
				inv.name,
			)
			inv_qty = flt(item_sum[0][0]) if item_sum else 0.0

		allocated_qty = inv_qty * (pct / 100.0)
		st = inv.sales_type or _("Unassigned")

		type_qty_map[st] = type_qty_map.get(st, 0.0) + allocated_qty
		total_qty += allocated_qty

		invoice_details.append(
			{
				"invoice": inv.name,
				"posting_date": str(inv.posting_date),
				"sales_type": inv.sales_type,
				"total_qty": inv_qty,
				"allocated_qty": allocated_qty,
			}
		)

	# Load Commission Rule Settings
	settings = frappe.get_single("Commission Rule Settings")
	calculation_basis = getattr(settings, "calculation_basis", "Fixed Flat Amount") or "Fixed Flat Amount"
	rules = [r for r in getattr(settings, "commission_rule", []) if r.enable]

	total_commission = 0.0
	breakdown = []

	for sales_type, qty in type_qty_map.items():
		type_rules = [r for r in rules if r.sales_type == sales_type]
		# Sort by from_qty, then to_qty ascending
		type_rules.sort(key=lambda r: (flt(r.from_qty), flt(r.to_qty)))

		matched_rule = None
		for r in type_rules:
			from_q = flt(r.from_qty)
			to_q = flt(r.to_qty)

			if to_q > 0:
				if from_q <= qty <= to_q:
					matched_rule = r
			else:
				if qty >= from_q:
					matched_rule = r

		# If qty exceeds the highest bracket to_qty, apply the highest bracket
		if not matched_rule and type_rules:
			highest_rule = type_rules[-1]
			if flt(highest_rule.to_qty) > 0 and qty >= flt(highest_rule.from_qty):
				matched_rule = highest_rule

		comm = 0.0
		bracket_str = ""

		if matched_rule:
			rule_amt = flt(matched_rule.amount)
			if calculation_basis == "Per Unit Rate (Qty * Amount)":
				comm = qty * rule_amt
			else:
				comm = rule_amt

			to_display = matched_rule.to_qty if flt(matched_rule.to_qty) > 0 else _("Unlimited")
			bracket_str = f"{matched_rule.from_qty} - {to_display}"
		elif type_rules:
			bracket_str = _("Below minimum target ({0})").format(type_rules[0].from_qty)
		else:
			bracket_str = _("No active rules for this Sales Type")

		total_commission += comm
		breakdown.append(
			{
				"sales_type": sales_type,
				"qty": qty,
				"bracket": bracket_str,
				"commission": comm,
				"amount": flt(matched_rule.amount) if matched_rule else 0.0,
			}
		)

	return {
		"total_qty": total_qty,
		"commission_amount": total_commission,
		"invoice_count": len(invoices),
		"details": breakdown,
		"invoices": invoice_details,
	}
