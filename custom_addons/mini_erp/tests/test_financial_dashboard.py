# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields

class TestFinancialDashboard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set up test data
        cls.partner = cls.env['res.partner'].create({
            'name': 'Financial Test Partner',
            'is_customer': True,
            'is_vendor': True,
            'partner_type': 'company',
        })

        # 1. Customer Invoice
        cls.invoice = cls.env['financial.invoice'].create({
            'partner_id': cls.partner.id,
            'amount': 10000.0,
            'type': 'out_invoice',
            'state': 'paid',
        })

        # 2. Supplier Bill
        cls.bill = cls.env['financial.invoice'].create({
            'partner_id': cls.partner.id,
            'amount': 4000.0,
            'type': 'in_invoice',
            'state': 'paid',
        })

        # 3. Operational Expense
        cls.expense = cls.env['operational.expense'].create({
            'name': 'Office Supplies',
            'category': 'operations',
            'amount': 1500.0,
        })

    def test_invoice_creation(self):
        """Test that invoices are correctly created with correct states and types."""
        self.assertEqual(self.invoice.state, 'paid')
        self.assertEqual(self.invoice.type, 'out_invoice')
        self.assertEqual(self.bill.type, 'in_invoice')
        self.assertTrue(self.invoice.name.startswith('INV/'))
        self.assertTrue(self.bill.name.startswith('BILL/'))

    def test_expense_creation(self):
        """Test that operational expenses are correctly stored."""
        self.assertEqual(self.expense.category, 'operations')
        self.assertEqual(self.expense.amount, 1500.0)

    def test_financial_calculations(self):
        """Test search and aggregation logic for financial totals."""
        invoices = self.env['financial.invoice'].search([
            ('type', '=', 'out_invoice'),
            ('state', '=', 'paid'),
            ('partner_id', '=', self.partner.id)
        ])
        tot_rev = sum(invoices.mapped('amount'))
        self.assertEqual(tot_rev, 10000.0)

        bills = self.env['financial.invoice'].search([
            ('type', '=', 'in_invoice'),
            ('state', '=', 'paid'),
            ('partner_id', '=', self.partner.id)
        ])
        tot_exp = sum(bills.mapped('amount'))
        self.assertEqual(tot_exp, 4000.0)

        expenses = self.env['operational.expense'].search([
            ('category', '=', 'operations'),
            ('name', '=', 'Office Supplies')
        ])
        tot_op = sum(expenses.mapped('amount'))
        self.assertEqual(tot_op, 1500.0)

