import sys
import os
# Add Odoo path to sys.path so we can import 'odoo'
sys.path.append(os.path.abspath('odoo'))

import odoo
# pyrefly: ignore [missing-import]
from odoo.api import Environment

def main():
    print("Loading Odoo configuration...")
    odoo.tools.config.parse_config(['-c', 'odoo.conf'])
    db_name = odoo.tools.config['db_name'] or 'mini_erp'
    
    print(f"Connecting to database: {db_name}...")
    registry = odoo.registry(db_name)
    
    with registry.cursor() as cr:
        env = Environment(cr, odoo.SUPERUSER_ID, {})
        
        # Find the draft MO loaded from demo data
        mo = env['mrp.production'].search([('state', '=', 'draft')], limit=1)
        if not mo:
            print("ERROR: No draft Manufacturing Order found!")
            sys.exit(1)
            
        print(f"Found Draft MO: {mo.name} for product {mo.product_id.name} (qty: {mo.product_qty})")
        
        # Verify initial quantities of components
        print("\n--- Verifying Initial Quantities ---")
        for comp_line in mo.bom_id.component_ids:
            p = comp_line.product_id
            print(f"Product: {p.name} | On Hand: {p.on_hand_qty} | Reserved: {p.reserved_qty} | Free: {p.free_to_use_qty}")
            
        # 1. Confirm MO
        print("\n--- Step 1: Confirming MO ---")
        mo.action_confirm()
        print(f"MO State after confirm: {mo.state}")
        
        # Verify components exploded and reserved
        print("\nExploded Components and Reservations:")
        for comp in mo.component_ids:
            print(f"- {comp.product_id.name}: Needed: {comp.quantity_needed} | Reserved: {comp.quantity_reserved} | Consumed: {comp.quantity_consumed}")
            # Ensure reservation works: Screws, Wooden Legs, Wooden Top should have reserved values
            if comp.quantity_reserved <= 0:
                print(f"ERROR: Reservation failed for {comp.product_id.name}!")
                sys.exit(1)
                
        # Verify work orders created
        print("\nCreated Work Orders:")
        for wo in mo.work_order_ids:
            print(f"- WO: {wo.name} | Work Center: {wo.work_center_id.name} | Duration: {wo.duration_minutes}m | State: {wo.state}")
            if wo.state != 'pending':
                print(f"ERROR: Work Order state should be 'pending', found '{wo.state}'!")
                sys.exit(1)
                
        # Verify updated product reserved quantities
        print("\nProduct Quantities after MO Confirm:")
        for comp in mo.component_ids:
            p = comp.product_id
            # Force recompute since we're in the same transaction
            p._compute_quantities()
            print(f"Product: {p.name} | On Hand: {p.on_hand_qty} | Reserved: {p.reserved_qty} | Free: {p.free_to_use_qty}")
            
        # 2. Start MO
        print("\n--- Step 2: Starting MO ---")
        mo.action_start()
        print(f"MO State after start: {mo.state}")
        for wo in mo.work_order_ids:
            if wo.state != 'ready':
                print(f"ERROR: Work Order state should be 'ready', found '{wo.state}'!")
                sys.exit(1)
                
        # 3. Process Work Orders (Mark them all as done)
        print("\n--- Step 3: Completing Work Orders ---")
        for wo in mo.work_order_ids:
            wo.action_start()
            print(f"Work Order '{wo.name}' state after start: {wo.state}")
            wo.action_done()
            print(f"Work Order '{wo.name}' state after complete: {wo.state}")
            if wo.state != 'done':
                print(f"ERROR: Work Order did not transition to 'done'!")
                sys.exit(1)
                
        # 4. Finish MO
        print("\n--- Step 4: Finishing MO ---")
        # Save initial on hand quantities of finished product
        finish_product = mo.product_id
        finish_product._compute_quantities()
        initial_finished_on_hand = finish_product.on_hand_qty
        
        mo.action_finish()
        print(f"MO State after finish: {mo.state}")
        if mo.state != 'done':
            print("ERROR: MO state should be 'done'!")
            sys.exit(1)
            
        # Verify stock updates
        print("\n--- Step 5: Verifying Stock Ledger and Quantities after Finish ---")
        finish_product._compute_quantities()
        print(f"Finished Product '{finish_product.name}' On Hand Qty: {finish_product.on_hand_qty} (expected increase: {mo.product_qty})")
        if finish_product.on_hand_qty != initial_finished_on_hand + mo.product_qty:
            print("ERROR: Finished product stock was not credited correctly!")
            sys.exit(1)
            
        print("\nComponents quantities after finish:")
        for comp in mo.component_ids:
            p = comp.product_id
            p._compute_quantities()
            print(f"Product: {p.name} | On Hand: {p.on_hand_qty} | Reserved: {p.reserved_qty} | Free: {p.free_to_use_qty}")
            if comp.quantity_reserved != 0:
                print(f"ERROR: Reservations were not released for {p.name}!")
                sys.exit(1)
                
        # Verify ledger entries created
        print("\nRecent Stock Ledger Entries:")
        ledgers = env['stock.ledger'].search([('reference', '=', mo.name)])
        for led in ledgers:
            print(f"- Date: {led.date} | Product: {led.product_id.name} | Type: {led.transaction_type} | Qty: {led.quantity} | Balance: {led.balance_after}")
            
        # Expecting entries for component consumption (negative qty) and finished goods receipt (positive qty)
        component_ledger_entries = ledgers.filtered(lambda l: l.transaction_type == 'manufacture_out')
        finished_ledger_entries = ledgers.filtered(lambda l: l.transaction_type == 'manufacture_in')
        
        if len(component_ledger_entries) != len(mo.component_ids):
            print("ERROR: Incomplete component consumption ledger logs!")
            sys.exit(1)
        if len(finished_ledger_entries) != 1:
            print("ERROR: Finished goods receipt ledger entry not logged!")
            sys.exit(1)
            
        print("\n=== VERIFICATION SUCCESSFUL! ===")
        # Rollback so we don't commit these changes to db, leaving the demo data in draft for user testing
        cr.rollback()
        print("Database transaction rolled back successfully.")

if __name__ == '__main__':
    main()
