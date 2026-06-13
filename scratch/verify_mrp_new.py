import sys
import os
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
            
        print(f"Found Draft MO: {mo.name} | Component Status: {mo.component_status}")
        
        # 1. Confirm MO
        print("\n--- Step 1: Confirming MO ---")
        mo.action_confirm()
        print(f"MO State after confirm: {mo.state}")
        print(f"Component Status after confirm: {mo.component_status}")
        if mo.component_status != 'available':
            print("ERROR: Component Status should be 'available'!")
            sys.exit(1)
            
        # 2. Produce MO (convenience method)
        print("\n--- Step 2: Running action_produce() ---")
        mo.action_produce()
        print(f"MO State after Produce: {mo.state}")
        if mo.state != 'done':
            print("ERROR: MO state should be 'done' after Produce!")
            sys.exit(1)
            
        # 3. Check Work Orders Done and Real Duration populated
        print("\n--- Step 3: Verifying Work Orders and Real Duration ---")
        for wo in mo.work_order_ids:
            print(f"- WO: {wo.name} | State: {wo.state} | Real Duration: {wo.real_duration} min")
            if wo.state != 'done':
                print(f"ERROR: Work order {wo.name} was not completed by action_produce()!")
                sys.exit(1)
                
        # 4. Check BoM save method
        print("\n--- Step 4: Testing BoM dummy action_save() ---")
        bom = mo.bom_id
        if not bom:
            print("ERROR: No BoM on MO!")
            sys.exit(1)
        res = bom.action_save()
        print(f"BoM Save returns: {res}")
        if not res:
            print("ERROR: BoM save returned False!")
            sys.exit(1)

        print("\n=== MOCKUP FEATURES VERIFICATION SUCCESSFUL! ===")
        cr.rollback()

if __name__ == '__main__':
    main()
