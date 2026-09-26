# Inventory Policy
Available quantity equals on_hand minus reserved.
Reservations hold stock for 24 hours.
Never promise stock without check_inventory.
Insufficient stock must stop order creation or trigger backorder workflow.
Release inventory on order cancel.
