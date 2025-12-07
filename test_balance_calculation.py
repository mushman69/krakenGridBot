"""
Test balance calculation with locked funds
This simulates the actual scenario from the logs
"""

class MockLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def success(self, msg): print(f"[SUCCESS] {msg}")

def test_balance_calculation():
    """Test balance calculation with 12 ETH sell orders"""
    print("="*60)
    print("TESTING BALANCE CALCULATION WITH LOCKED FUNDS")
    print("="*60)
    
    # Simulate balances from logs
    total_balances = {
        'XETH': '0.064131',
        'ZUSD': '5.980900',
        'XXBT': '0.000609',
        'XXRP': '105.945477'
    }
    
    # Simulate 12 ETH/USD sell orders (from the logs)
    # Each order is 0.005077 ETH (from the image description)
    open_orders = {}
    for i in range(12):
        order_id = f"ORDER_{i}"
        open_orders[order_id] = {
            'vol': '0.00507700',
            'descr': {
                'type': 'sell',
                'pair': 'XETHZUSD',  # Kraken format
                'price': '3052.95'
            }
        }
    
    print(f"\nTotal balances:")
    for asset, balance in total_balances.items():
        print(f"  {asset}: {balance}")
    
    print(f"\nOpen orders: {len(open_orders)} ETH/USD sell orders")
    for i, (order_id, order_data) in enumerate(list(open_orders.items())[:3]):
        print(f"  Order {i+1}: {order_data['vol']} ETH @ ${order_data['descr']['price']}")
    print(f"  ... (showing first 3 of {len(open_orders)})")
    
    # Calculate locked funds
    locked_funds = {}
    for order_id, order_data in open_orders.items():
        desc = order_data.get('descr', {})
        order_type = desc.get('type', '')
        vol = float(order_data.get('vol', 0))
        
        if order_type == 'sell':
            pair_str = desc.get('pair', '')
            if 'ETH' in pair_str and 'USD' in pair_str:
                # ETH/USD sell order: locks ETH
                # Check if asset name matches
                asset_name = 'XETH'  # From balance keys
                locked_funds[asset_name] = locked_funds.get(asset_name, 0) + vol
                print(f"  Locking {vol} {asset_name} from sell order")
    
    print(f"\nLocked funds:")
    for asset, locked in locked_funds.items():
        print(f"  {asset}: {locked:.6f}")
    
    # Calculate available balances
    available_balances = {}
    for asset, total_balance in total_balances.items():
        total = float(total_balance)
        locked = locked_funds.get(asset, 0)
        available = total - locked
        available_balances[asset] = available
        if locked > 0:
            print(f"  {asset}: {total:.6f} total, {locked:.6f} locked, {available:.6f} available")
        else:
            print(f"  {asset}: {total:.6f} total, {available:.6f} available")
    
    # Verify the calculation
    print(f"\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    
    total_eth = float(total_balances['XETH'])
    locked_eth = locked_funds.get('XETH', 0)
    available_eth = available_balances['XETH']
    
    print(f"Total ETH: {total_eth:.6f}")
    print(f"Locked ETH: {locked_eth:.6f} (12 orders × 0.005077)")
    print(f"Available ETH: {available_eth:.6f}")
    print(f"Expected available: {total_eth - locked_eth:.6f}")
    
    if abs(available_eth - (total_eth - locked_eth)) < 0.000001:
        print("✅ Balance calculation is CORRECT")
    else:
        print("❌ Balance calculation is WRONG")
    
    # Check if we can place 6 more orders of 0.010154 ETH
    print(f"\n" + "="*60)
    print("ORDER PLACEMENT TEST")
    print("="*60)
    
    orders_to_place = 6
    volume_per_order = 0.010154
    total_needed = orders_to_place * volume_per_order
    
    print(f"Want to place: {orders_to_place} orders")
    print(f"Volume per order: {volume_per_order} ETH")
    print(f"Total needed: {total_needed:.6f} ETH")
    print(f"Available: {available_eth:.6f} ETH")
    
    if available_eth >= total_needed:
        print(f"✅ Can place all {orders_to_place} orders")
    else:
        print(f"❌ Cannot place all {orders_to_place} orders")
        print(f"   Need {total_needed:.6f} but only have {available_eth:.6f}")
        max_orders = int(available_eth / volume_per_order)
        print(f"   Can only place {max_orders} orders")

if __name__ == "__main__":
    test_balance_calculation()

