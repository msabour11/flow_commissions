// Copyright (c) 2026, Mohamed AbdElsabour and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Person', {
	refresh: function (frm) {
		// Custom enhancements on Sales Person form if needed
	}
});

frappe.ui.form.on('Commission Details', {
	fetch_commission: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (!row.from_date || !row.to_date) {
			frappe.msgprint({
				title: __('Missing Date Range'),
				indicator: 'orange',
				message: __('Please select both <b>From Date</b> and <b>To Date</b> before fetching commission.')
			});
			return;
		}

		if (row.from_date > row.to_date) {
			frappe.msgprint({
				title: __('Invalid Date Range'),
				indicator: 'red',
				message: __('<b>From Date</b> cannot be after <b>To Date</b>.')
			});
			return;
		}

		if (frm.is_new()) {
			frappe.msgprint({
				title: __('Document Not Saved'),
				indicator: 'orange',
				message: __('Please save the Sales Person record first.')
			});
			return;
		}

		frappe.call({
			method: 'flow_commissions.flow_commissions.doctype.commission_rule_settings.commission_rule_settings.fetch_commission_for_row',
			args: {
				sales_person: frm.doc.name,
				from_date: row.from_date,
				to_date: row.to_date
			},
			freeze: true,
			freeze_message: __('Calculating Sales Commission...'),
			callback: function (r) {
				if (r.exc) {
					frappe.msgprint({
						title: __('Error'),
						indicator: 'red',
						message: __('An error occurred while calculating commission.')
					});
					return;
				}

				if (r.message) {
					let res = r.message;
					frappe.model.set_value(cdt, cdn, 'total_qty', res.total_qty || 0);
					frappe.model.set_value(cdt, cdn, 'qty', res.total_qty || 0);
					frappe.model.set_value(cdt, cdn, 'commission_amount', res.commission_amount || 0);

					let currency = frappe.defaults.get_default('currency') || '';
					let format_amt = function (val) {
						return format_currency(val, currency);
					};

					let summary_html = `
						<div style="font-size: 13px; line-height: 1.6;">
							<p style="margin-bottom: 8px;">
								${__('Found <b>{0}</b> submitted Sales Invoice(s) between <b>{1}</b> and <b>{2}</b>.', [
									res.invoice_count,
									row.from_date,
									row.to_date
								])}
							</p>
							<div class="row" style="margin-bottom: 12px;">
								<div class="col-xs-6">
									<div class="well well-sm" style="margin: 0; padding: 8px; text-align: center; background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 6px;">
										<div style="font-size: 11px; color: #718096; text-transform: uppercase;">${__('Total Qty')}</div>
										<div style="font-size: 18px; font-weight: bold; color: #2d3748;">${res.total_qty}</div>
									</div>
								</div>
								<div class="col-xs-6">
									<div class="well well-sm" style="margin: 0; padding: 8px; text-align: center; background: #f0fff4; border: 1px solid #c6f6d5; border-radius: 6px;">
										<div style="font-size: 11px; color: #38a169; text-transform: uppercase;">${__('Commission Amount')}</div>
										<div style="font-size: 18px; font-weight: bold; color: #22543d;">${format_amt(res.commission_amount)}</div>
									</div>
								</div>
							</div>
					`;

					if (res.details && res.details.length > 0) {
						summary_html += `
							<table class="table table-bordered table-condensed" style="margin-top: 10px; font-size: 12px;">
								<thead>
									<tr style="background-color: #f7fafc;">
										<th>${__('Sales Type')}</th>
										<th style="text-align: right;">${__('Qty Sold')}</th>
										<th>${__('Matched Bracket')}</th>
										<th style="text-align: right;">${__('Commission')}</th>
									</tr>
								</thead>
								<tbody>
						`;

						res.details.forEach(function (d) {
							summary_html += `
								<tr>
									<td><b>${frappe.utils.escape_html(d.sales_type)}</b></td>
									<td style="text-align: right;">${d.qty}</td>
									<td><span class="label label-default" style="font-size: 11px;">${frappe.utils.escape_html(d.bracket)}</span></td>
									<td style="text-align: right; font-weight: bold; color: #27ae60;">${format_amt(d.commission)}</td>
								</tr>
							`;
						});

						summary_html += `
								</tbody>
							</table>
						`;
					} else {
						summary_html += `<p class="text-muted" style="margin-top: 10px;">${__('No invoices with sales type found in this date range.')}</p>`;
					}

					summary_html += `</div>`;

					frappe.msgprint({
						title: __('Commission Calculation Result'),
						indicator: 'green',
						message: summary_html
					});
				}
			}
		});
	},

	create_je: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.commission_amount || row.commission_amount <= 0) {
			frappe.msgprint({
				title: __('No Commission'),
				indicator: 'orange',
				message: __('Commission amount is zero. Please fetch commission first.')
			});
			return;
		}

		frappe.msgprint({
			title: __('Create Journal Entry'),
			indicator: 'blue',
			message: __('Commission amount is <b>{0}</b>. Journal Entry creation flow is ready for account mapping.', [
				format_currency(row.commission_amount)
			])
		});
	}
});
