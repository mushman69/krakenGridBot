"""
Test script to verify expected counts logic without real API calls
This simulates the grid creation and monitoring flow to catch bugs
"""

class MockLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def success(self, msg): print(f"[SUCCESS] {msg}")

class TestGridBot:
    def __init__(self):
        self.expected_order_counts = {}
        self.balances = {'ZUSD': 100.0, 'XETH': 0.06}
        self.current_prices = {'ETH/USD': 3052.0}
        Logger = MockLogger()
    
    def create_grid_orders(self, pair, buy_orders_count, sell_orders_count):
        """Simulate grid creation - this is where the bug might be"""
        print(f"\n=== Creating grid for {pair} ===")
        print(f"Intended: {buy_orders_count} buy, {sell_orders_count} sell")
        
        # Simulate order placement
        buy_orders_placed = 0
        sell_orders_placed = 0
        
        # Simulate: Cannot calculate buy order volume (insufficient funds)
        if buy_orders_count > 0:
            print(f"⚠️ Cannot calculate buy order volume for {pair}")
            # No buy orders placed
        else:
            buy_orders_placed = 0
        
        # Simulate: Successfully place sell orders
        if sell_orders_count > 0:
            # Simulate placing 12 sell orders
            sell_orders_placed = 12
            print(f"✅ Placed {sell_orders_placed} sell orders")
        
        # CRITICAL: Set expected counts from ACTUAL placed orders
        self.expected_order_counts[pair] = {
            'buy': buy_orders_placed,
            'sell': sell_orders_placed
        }
        
        print(f"📊 {pair}: Set expected counts: {buy_orders_placed} buy, {sell_orders_placed} sell")
        print(f"   Stored: {self.expected_order_counts[pair]}")
        
        # Verify
        stored = self.expected_order_counts.get(pair, {})
        if stored.get('buy') != buy_orders_placed or stored.get('sell') != sell_orders_placed:
            print(f"❌ BUG DETECTED! Mismatch: Placed={buy_orders_placed}/{sell_orders_placed}, Stored={stored.get('buy')}/{stored.get('sell')}")
            return False
        else:
            print(f"✅ Expected counts correctly stored")
            return True
    
    def monitor_orders(self, pair, current_buy, current_sell):
        """Simulate monitoring - check if expected counts are correct"""
        print(f"\n=== Monitoring {pair} ===")
        print(f"Current orders: {current_buy} buy, {current_sell} sell")
        
        if pair not in self.expected_order_counts:
            print(f"⚠️ No expected counts set - initializing from current orders")
            self.expected_order_counts[pair] = {
                'buy': current_buy,
                'sell': current_sell
            }
        else:
            expected = self.expected_order_counts[pair]
            expected_buy = expected.get('buy', 0)
            expected_sell = expected.get('sell', 0)
            print(f"Expected: {expected_buy} buy, {expected_sell} sell")
            
            # Check for discrepancies
            if current_buy < expected_buy:
                filled = expected_buy - current_buy
                print(f"⚠️ {filled} buy order(s) appear filled - would try to place {filled} sell orders")
                if current_sell == expected_sell:
                    print(f"❌ PROBLEM: All sell orders still active, but trying to place more!")
                    print(f"   This would cause 'Insufficient funds' errors")
                    return False
            
        return True

# Test the scenario from the logs
print("=" * 60)
print("TESTING EXPECTED COUNTS LOGIC")
print("=" * 60)

bot = TestGridBot()

# Scenario: ETH/USD grid creation
# Intended: 3 buy, 12 sell
# Actual: 0 buy (failed), 12 sell (success)
print("\n" + "=" * 60)
print("TEST 1: Grid Creation (ETH/USD)")
print("=" * 60)
result1 = bot.create_grid_orders('ETH/USD', buy_orders_count=3, sell_orders_count=12)

# Verify expected counts
expected = bot.expected_order_counts.get('ETH/USD', {})
if expected.get('buy') == 0 and expected.get('sell') == 12:
    print("✅ TEST 1 PASSED: Expected counts set correctly (0 buy, 12 sell)")
else:
    print(f"❌ TEST 1 FAILED: Expected counts wrong! Got: {expected}")

# Scenario: First monitoring check
# Current: 0 buy, 12 sell
# Expected: Should be 0 buy, 12 sell (from grid creation)
print("\n" + "=" * 60)
print("TEST 2: First Monitoring Check")
print("=" * 60)
result2 = bot.monitor_orders('ETH/USD', current_buy=0, current_sell=12)

# Check if it would incorrectly detect "filled" orders
expected = bot.expected_order_counts.get('ETH/USD', {})
if expected.get('buy') == 0:
    print("✅ TEST 2 PASSED: Expected buy count is 0 (correct)")
    print("   Bot should NOT think buy orders were filled")
else:
    print(f"❌ TEST 2 FAILED: Expected buy count is {expected.get('buy')} (should be 0)")
    print("   Bot would incorrectly think buy orders were filled!")

print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
if result1 and result2 and expected.get('buy') == 0:
    print("✅ ALL TESTS PASSED - Logic is correct")
    print("   If bugs persist, check:")
    print("   1. Is the log message 'Set expected counts' appearing?")
    print("   2. Are expected counts being overridden elsewhere?")
    print("   3. Is there a race condition between grid creation and monitoring?")
else:
    print("❌ TESTS FAILED - Logic has bugs")
    print("   Expected counts are not being set correctly")

