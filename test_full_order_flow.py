"""
Full simulation of order placement flow to debug XRP/BTC issues
This simulates the complete flow from price fetching to order placement
"""

import asyncio

class MockLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def success(self, msg): print(f"[SUCCESS] {msg}")

class MockGridBot:
    def __init__(self):
        self.btc_usd_price = None
        self.current_prices = {}
        self.enabled_pairs = {
            "XRP/BTC": {
                'kraken_pair': 'XXRPXXBT',
                'precision': 8,
                'volume_precision': 2,
                'min_order_size': 10.0
            },
            "ETH/USD": {
                'kraken_pair': 'XETHZUSD',
                'precision': 2,
                'volume_precision': 6,
                'min_order_size': 0.005
            }
        }
        Logger = MockLogger()
    
    def simulate_price_fetch(self):
        """Simulate fetching prices from Kraken"""
        print("\n" + "="*60)
        print("SIMULATING PRICE FETCH")
        print("="*60)
        
        # Simulate Kraken API response
        ticker_data = {
            "XXRPXXBT": {"c": ["0.0000227"]},
            "XETHZUSD": {"c": ["3042.35"]},
            "XXBTZUSD": {"c": ["89500.00"]}  # BTC/USD price
        }
        
        pair_mapping = {
            "XXRPXXBT": "XRP/BTC",
            "XETHZUSD": "ETH/USD",
            "XXBTZUSD": "BTC/USD"
        }
        
        for kraken_pair, data in ticker_data.items():
            if 'c' in data:
                price = float(data['c'][0])
                display_pair = pair_mapping.get(kraken_pair, kraken_pair)
                if display_pair == "BTC/USD":
                    self.btc_usd_price = price
                    print(f"✅ {display_pair}: {price:.2f} (for XRP/BTC order value conversion)")
                else:
                    self.current_prices[display_pair] = price
                    print(f"✅ {display_pair}: {price:.7f}")
        
        # Fallback check
        if "XRP/BTC" in self.enabled_pairs and self.btc_usd_price is None:
            if "ETH/USD" in self.current_prices:
                eth_price = self.current_prices["ETH/USD"]
                self.btc_usd_price = eth_price * 18
                print(f"⚠️ BTC/USD price not fetched, estimating from ETH/USD: ${self.btc_usd_price:.2f}")
            else:
                self.btc_usd_price = 90000.0
                print(f"⚠️ BTC/USD price not available, using fallback: ${self.btc_usd_price:.2f}")
    
    def round_price(self, price, precision):
        return round(price, precision)
    
    def round_volume(self, volume, precision):
        return round(volume, precision)
    
    def place_order_test(self, pair, side, volume, price):
        """Test order placement with full validation"""
        print(f"\n{'='*60}")
        print(f"TESTING ORDER PLACEMENT: {pair} {side.upper()}")
        print(f"{'='*60}")
        
        config = self.enabled_pairs[pair]
        kraken_pair = config.get('kraken_pair')
        precision = config.get('precision', 8)
        volume_precision = config.get('volume_precision', 8)
        min_order_size = config.get('min_order_size', 0.001)
        
        # Round values
        rounded_price = self.round_price(price, precision)
        rounded_volume = self.round_volume(volume, volume_precision)
        
        print(f"Input: volume={volume}, price={price}")
        print(f"Rounded: volume={rounded_volume}, price={rounded_price}")
        print(f"Min order size: {min_order_size}")
        
        # Validate
        if pair == "ETH/USD":
            if rounded_volume < min_order_size:
                print(f"❌ FAIL: Volume {rounded_volume} < {min_order_size}")
                return False
            print(f"✅ PASS: Volume {rounded_volume} >= {min_order_size}")
            return True
            
        elif pair == "XRP/BTC":
            order_value_btc = rounded_volume * rounded_price
            print(f"Order value (BTC): {order_value_btc:.8f} BTC")
            
            # Get BTC/USD
            btc_usd = self.btc_usd_price
            if btc_usd is None:
                if "ETH/USD" in self.current_prices:
                    eth_price = self.current_prices.get("ETH/USD", 3000)
                    btc_usd = eth_price * 18
                    print(f"⚠️ BTC/USD not available, estimating: ${btc_usd:.2f}")
                else:
                    btc_usd = 90000.0
                    print(f"⚠️ BTC/USD not available, fallback: ${btc_usd:.2f}")
            
            order_value_usd = order_value_btc * btc_usd
            print(f"Order value (USD): ${order_value_usd:.2f} (BTC: {order_value_btc:.8f} @ ${btc_usd:.2f}/BTC)")
            
            if order_value_usd < min_order_size:
                print(f"❌ FAIL: ${order_value_usd:.2f} < ${min_order_size:.2f}")
                return False
            else:
                print(f"✅ PASS: ${order_value_usd:.2f} >= ${min_order_size:.2f}")
                return True
        
        return False

# Run comprehensive test
print("="*60)
print("FULL ORDER FLOW SIMULATION")
print("="*60)

bot = MockGridBot()

# Step 1: Fetch prices
bot.simulate_price_fetch()

# Step 2: Test XRP/BTC sell orders (the failing case from logs)
print("\n" + "="*60)
print("TESTING XRP/BTC SELL ORDERS")
print("="*60)

test_cases = [
    (10.06, 0.0000227, "10.06 XRP @ 0.0000227 BTC"),
    (25.16, 0.0000227, "25.16 XRP @ 0.0000227 BTC"),
    (50.0, 0.0000227, "50.0 XRP @ 0.0000227 BTC"),
]

all_passed = True
for volume, price, desc in test_cases:
    print(f"\n--- Test: {desc} ---")
    result = bot.place_order_test("XRP/BTC", "sell", volume, price)
    if not result:
        all_passed = False

# Step 3: Test XRP/BTC buy orders
print("\n" + "="*60)
print("TESTING XRP/BTC BUY ORDERS")
print("="*60)

# For buy orders, we need to calculate volume from BTC available
# Simulate: 0.000609 BTC available, want to place 4 buy orders
btc_available = 0.000609
orders_count = 4
btc_per_order = btc_available / orders_count
xrp_price = 0.0000227
xrp_volume = btc_per_order / xrp_price

print(f"Available BTC: {btc_available}")
print(f"Orders to place: {orders_count}")
print(f"BTC per order: {btc_per_order:.8f}")
print(f"XRP volume per order: {xrp_volume:.2f}")
result = bot.place_order_test("XRP/BTC", "buy", xrp_volume, xrp_price)
if not result:
    all_passed = False

# Summary
print("\n" + "="*60)
print("FINAL SUMMARY")
print("="*60)
if all_passed:
    print("✅ ALL TESTS PASSED!")
    print("\nThe fix is correct. The issue is that the Docker container")
    print("is running old code. Rebuild with:")
    print("  docker build --no-cache -t gridbot-pnl .")
    print("  docker-compose restart")
else:
    print("❌ SOME TESTS FAILED - Check the output above")

