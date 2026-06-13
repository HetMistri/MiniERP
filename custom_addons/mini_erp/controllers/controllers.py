# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import http, fields
from odoo.http import request


class MiniErpDashboardController(http.Controller):

    @http.route('/dashboard/data', type='json', auth='user', methods=['POST'])
    def get_dashboard_data(self):
        sale_order_model = request.env['sale.order']
        purchase_order_model = request.env['purchase.order']
        mrp_production_model = request.env['mrp.production']
        product_product_model = request.env['product.product']
        audit_log_model = request.env['audit.log']

        products = product_product_model.search([('product_type', '=', 'stockable')])
        low_stock_count = len(products.filtered(lambda p: p.free_to_use_qty <= 0))

        audit_logs = audit_log_model.search([], limit=10)
        audit_logs_list = [{
            'id': log.id,
            'model_name': log.model_name,
            'record_id': log.record_id,
            'field_name': log.field_name or '',
            'old_value': log.old_value or '',
            'new_value': log.new_value or '',
            'action': log.action,
            'user': log.user_id.name,
            'timestamp': fields.Datetime.to_string(log.timestamp),
            'display_name': log.display_name or ''
        } for log in audit_logs]

        data = {
            'total_sales_orders': sale_order_model.search_count([]),
            'pending_deliveries': sale_order_model.search_count([('state', 'in', ('confirmed', 'partially_delivered'))]),
            'total_mo': mrp_production_model.search_count([]) if 'mrp.production' in request.env else 0,
            'delayed_orders': sale_order_model.search_count([
                ('state', 'in', ('confirmed', 'partially_delivered')),
                ('expected_date', '<', fields.Date.today())
            ]),
            'total_po': purchase_order_model.search_count([]),
            'partial_receipts': purchase_order_model.search_count([('state', '=', 'partially_received')]),
            'low_stock_products': low_stock_count,
            'recent_audit_logs': audit_logs_list,
        }
        return data

    @http.route('/dashboard/financial_data', type='json', auth='user', methods=['POST'])
    def get_financial_data(self, filter_type='this_month', date_start=None, date_end=None):
        import datetime
        from dateutil.relativedelta import relativedelta
        from odoo.tools import date_utils

        today = fields.Date.today()
        
        # Calculate date range
        if filter_type == 'today':
            start_date = today
            end_date = today
        elif filter_type == 'this_week':
            start_date = date_utils.start_of(today, 'week')
            end_date = date_utils.end_of(today, 'week')
        elif filter_type == 'this_month':
            start_date = today.replace(day=1)
            end_date = date_utils.end_of(today, 'month')
        elif filter_type == 'this_quarter':
            start_date = date_utils.start_of(today, 'quarter')
            end_date = date_utils.end_of(today, 'quarter')
        elif filter_type == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        elif filter_type == 'custom':
            start_date = fields.Date.to_date(date_start) if date_start else today.replace(day=1)
            end_date = fields.Date.to_date(date_end) if date_end else today
        else:
            start_date = today.replace(day=1)
            end_date = date_utils.end_of(today, 'month')

        # Convert date to datetime bounds
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)

        # Calculate previous period for growth calculations
        if filter_type == 'today':
            prev_start = start_date - datetime.timedelta(days=1)
            prev_end = end_date - datetime.timedelta(days=1)
        elif filter_type == 'this_week':
            prev_start = start_date - datetime.timedelta(weeks=1)
            prev_end = end_date - datetime.timedelta(weeks=1)
        elif filter_type == 'this_month':
            prev_start = start_date - relativedelta(months=1)
            prev_end = start_date - datetime.timedelta(days=1)
        elif filter_type == 'this_quarter':
            prev_start = start_date - relativedelta(months=3)
            prev_end = start_date - datetime.timedelta(days=1)
        elif filter_type == 'this_year':
            prev_start = start_date - relativedelta(years=1)
            prev_end = start_date - datetime.timedelta(days=1)
        else:
            delta = end_date - start_date + datetime.timedelta(days=1)
            prev_start = start_date - delta
            prev_end = end_date - delta

        prev_start_datetime = datetime.datetime.combine(prev_start, datetime.time.min)
        prev_end_datetime = datetime.datetime.combine(prev_end, datetime.time.max)

        # Helper method for calculations
        def calculate_financials(d_start, d_end, dt_start, dt_end):
            # 1. Sales Orders
            so_domain = [('state', 'in', ('confirmed', 'partially_delivered', 'fully_delivered')), ('date_order', '>=', dt_start), ('date_order', '<=', dt_end)]
            sales_orders = request.env['sale.order'].search(so_domain)
            sales_val = sum(sales_orders.mapped('total_amount'))

            # 2. Deliveries Valuation
            ledger_domain = [('transaction_type', '=', 'sale_delivery'), ('date', '>=', dt_start), ('date', '<=', dt_end)]
            deliveries = request.env['stock.ledger'].search(ledger_domain)
            deliveries_val = sum(abs(move.quantity) * move.product_id.sale_price for move in deliveries)

            # 3. Customer Invoices
            inv_domain = [('type', '=', 'out_invoice'), ('state', '=', 'paid'), ('invoice_date', '>=', d_start), ('invoice_date', '<=', d_end)]
            invoices = request.env['financial.invoice'].search(inv_domain)
            invoices_val = sum(invoices.mapped('amount'))

            # Total Revenue
            tot_rev = sales_val + deliveries_val + invoices_val

            # 4. Purchases Orders
            po_domain = [('state', 'in', ('confirmed', 'partially_received', 'fully_received')), ('date_order', '>=', dt_start), ('date_order', '<=', dt_end)]
            purchases = request.env['purchase.order'].search(po_domain)
            purchases_val = sum(purchases.mapped('total_amount'))

            # 5. Supplier Bills
            bill_domain = [('type', '=', 'in_invoice'), ('state', '=', 'paid'), ('invoice_date', '>=', d_start), ('invoice_date', '<=', d_end)]
            bills = request.env['financial.invoice'].search(bill_domain)
            bills_val = sum(bills.mapped('amount'))

            # 6. Manufacturing Costs (Raw materials + Labor/Work Center)
            mo_domain = [('state', '=', 'done'), ('date_finished', '>=', dt_start), ('date_finished', '<=', dt_end)]
            mo_done = request.env['mrp.production'].search(mo_domain) if 'mrp.production' in request.env else []
            
            materials_cost = 0.0
            workcenter_cost = 0.0
            for mo in mo_done:
                materials_cost += sum(c.quantity_consumed * c.product_id.cost_price for c in mo.component_ids)
                workcenter_cost += sum((wo.real_duration / 60.0) * wo.work_center_id.cost_per_hour for wo in mo.work_order_ids if wo.work_center_id)
            mfg_val = materials_cost + workcenter_cost

            # 7. Operational Expenses
            exp_domain = [('date', '>=', d_start), ('date', '<=', d_end)]
            expenses = request.env['operational.expense'].search(exp_domain)
            op_exp_val = sum(expenses.mapped('amount'))

            # Total Expenses
            tot_exp = purchases_val + bills_val + mfg_val + op_exp_val

            return {
                'sales': sales_val,
                'deliveries': deliveries_val,
                'invoices': invoices_val,
                'revenue': tot_rev,
                'purchases': purchases_val,
                'bills': bills_val,
                'manufacturing': mfg_val,
                'operational': op_exp_val,
                'expenses': tot_exp,
                'profit': tot_rev - tot_exp,
                'raw_materials_mfg': materials_cost
            }

        # Compute current and previous financials
        current = calculate_financials(start_date, end_date, start_datetime, end_datetime)
        previous = calculate_financials(prev_start, prev_end, prev_start_datetime, prev_end_datetime)

        # Growth percentages
        def get_growth(curr, prev):
            if not prev:
                return 0.0
            return round(((curr - prev) / prev) * 100, 1)

        rev_growth = get_growth(current['revenue'], previous['revenue'])
        exp_growth = get_growth(current['expenses'], previous['expenses'])

        # Company configuration (Opening Balance)
        company = request.env.company
        opening_balance = company.opening_balance or 100000.0
        remaining_balance = opening_balance + current['revenue'] - current['expenses']
        
        # Cash utilization
        total_avail = opening_balance + current['revenue']
        cash_utilization = round((current['expenses'] / total_avail) * 100, 1) if total_avail else 0.0
        cash_utilization = min(cash_utilization, 100.0)

        # Revenue Breakdown categories (Sales, Mfg, Service, Other)
        # We classify sale order lines
        sales_orders_all = request.env['sale.order'].search([('state', 'in', ('confirmed', 'partially_delivered', 'fully_delivered')), ('date_order', '>=', start_datetime), ('date_order', '<=', end_datetime)])
        
        sales_rev = 0.0
        mfg_rev = 0.0
        service_rev = 0.0
        for so in sales_orders_all:
            for line in so.order_line_ids:
                if line.product_id.product_type == 'service':
                    service_rev += line.subtotal
                elif line.product_id.procurement_type == 'manufacture':
                    mfg_rev += line.subtotal
                else:
                    sales_rev += line.subtotal
        
        other_rev = current['invoices'] + current['deliveries'] # items not in sales orders directly

        # Expense Breakdown categories
        # Raw materials cost is calculated from Manufacturing MO components
        # Purchases from POs
        # Payroll, Operations, Logistics, Miscellaneous from operational expenses
        exp_payroll = sum(request.env['operational.expense'].search([('category', '=', 'payroll'), ('date', '>=', start_date), ('date', '<=', end_date)]).mapped('amount'))
        exp_ops = sum(request.env['operational.expense'].search([('category', '=', 'operations'), ('date', '>=', start_date), ('date', '<=', end_date)]).mapped('amount'))
        exp_logistics = sum(request.env['operational.expense'].search([('category', '=', 'logistics'), ('date', '>=', start_date), ('date', '<=', end_date)]).mapped('amount'))
        exp_misc = sum(request.env['operational.expense'].search([('category', '=', 'misc'), ('date', '>=', start_date), ('date', '<=', end_date)]).mapped('amount'))

        # Profitability margin
        profit_margin = (current['profit'] / current['revenue']) * 100 if current['revenue'] > 0 else 0.0
        
        # Financial Health Score
        # Health Score = Profitability Margin (40%) + Cash Flow/Balance position (30%) + Revenue Growth score (30%)
        profitability_score = min(max(profit_margin * 2, 0.0), 40.0) # 20% margin gives full 40 points
        
        # Cash Flow score: based on cash utilization. Low utilization (but > 0) is good, meaning we have excess cash
        if cash_utilization <= 10:
            cash_score = 30.0
        elif cash_utilization <= 40:
            cash_score = 25.0
        elif cash_utilization <= 70:
            cash_score = 15.0
        elif cash_utilization <= 90:
            cash_score = 5.0
        else:
            cash_score = 0.0
            
        growth_score = min(max(rev_growth * 2.0, 0.0), 30.0) # 15% growth gives full 30 points
        
        health_score = int(profitability_score + cash_score + growth_score + 30.0) # baseline of 30
        health_score = min(max(health_score, 0), 100)
        
        health_status = 'Critical'
        if health_score >= 80:
            health_status = 'Excellent'
        elif health_score >= 60:
            health_status = 'Good'
        elif health_score >= 40:
            health_status = 'Average'

        # Today's indicators
        today_datetime_start = datetime.datetime.combine(today, datetime.time.min)
        today_datetime_end = datetime.datetime.combine(today, datetime.time.max)
        today_financials = calculate_financials(today, today, today_datetime_start, today_datetime_end)

        # YTD indicators
        ytd_start = today.replace(month=1, day=1)
        ytd_start_datetime = datetime.datetime.combine(ytd_start, datetime.time.min)
        ytd_financials = calculate_financials(ytd_start, today, ytd_start_datetime, today_datetime_end)

        # Generate Monthly Chart Data (Jan to Dec of the selected year)
        monthly_income_data = []
        monthly_expense_data = []
        monthly_profit_data = []
        
        selected_year = start_date.year
        for month in range(1, 13):
            m_start = datetime.date(selected_year, month, 1)
            # Find last day of month
            if month == 12:
                m_end = datetime.date(selected_year, month, 31)
            else:
                m_end = datetime.date(selected_year, month + 1, 1) - datetime.timedelta(days=1)
            
            m_dt_start = datetime.datetime.combine(m_start, datetime.time.min)
            m_dt_end = datetime.datetime.combine(m_end, datetime.time.max)
            
            m_fin = calculate_financials(m_start, m_end, m_dt_start, m_dt_end)
            
            monthly_income_data.append(m_fin['revenue'])
            monthly_expense_data.append(m_fin['expenses'])
            monthly_profit_data.append(m_fin['profit'])

        return {
            'kpis': {
                'revenue': current['revenue'],
                'revenue_growth': rev_growth,
                'expenses': current['expenses'],
                'expenses_growth': exp_growth,
                'profit': current['profit'],
                'remaining_balance': remaining_balance,
                'cash_utilization': cash_utilization,
            },
            'health': {
                'score': health_score,
                'status': health_status,
            },
            'charts': {
                'monthly_months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                'monthly_income': monthly_income_data,
                'monthly_expenses': monthly_expense_data,
                'monthly_profits': monthly_profit_data,
                'revenue_breakdown': {
                    'labels': ['Sales Revenue', 'Manufacturing Revenue', 'Service Revenue', 'Other Revenue'],
                    'values': [sales_rev, mfg_rev, service_rev, other_rev],
                },
                'expense_categories': {
                    'labels': ['Raw Materials', 'Purchases', 'Payroll', 'Operations', 'Logistics', 'Miscellaneous'],
                    'values': [current['raw_materials_mfg'], current['purchases'], exp_payroll, exp_ops, exp_logistics, exp_misc],
                }
            },
            'summary': {
                'today_income': today_financials['revenue'],
                'today_expenses': today_financials['expenses'],
                'month_profit': current['profit'],
                'ytd_revenue': ytd_financials['revenue'],
                'ytd_expenses': ytd_financials['expenses'],
                'ytd_profit': ytd_financials['profit'],
            }
        }

