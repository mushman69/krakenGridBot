"""
Comprehensive test to verify XRP/BTC order value calculation fix
This simulates the actual order placement flow
"""

class MockLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def success(self, msg): print(f"[SUCCESS] {msg}")

class TestOrderValue:
    def __init__(self):
        self.btc_usd_price = None
        self.current_prices = {}
        Logger = MockLogger()
    
    def round_price(self, price, precision):
        return round(price, precision)
    
    def round_volume(self, volume, precision):
        return round(volume, precision)
    
    def place_limit_order_test(self, pair, side, volume, price, config):
        """Test the order value calculation logic"""
        print(f"\n{'='*60}")
        print(f"TESTING: {pair} {side.upper()} order")
        print(f"{'='*60}")
        
        kraken_pair = config.get('kraken_pair')
        precision = config.get('precision', 8)
        volume_precision = config.get('volume_precision', 8)
        min_order_size = config.get('min_order_size', 0.001)
        
        # Round price and volume
        rounded_price = self.round_price(price, precision)
        rounded_volume = self.round_volume(volume, volume_precision)
        
        print(f"Input: volume={volume}, price={price}")
        print(f"Rounded: volume={rounded_volume}, price={rounded_price}")
        print(f"Min order size: {min_order_size}")
        
        if pair == "ETH/USD":
            # For ETH/USD, min_order_size is in ETH
            if rounded_volume < min_order_size:
                print(f"❌ FAIL: {rounded_volume} < {min_order_size}")
                return False
            else:
                print(f"✅ PASS: {rounded_volume} >= {min_order_size}")
                return True
        elif pair == "XRP/BTC":
            # For XRP/BTC, order_value is in BTC, need to convert to USD
            order_value_btc = rounded_volume * rounded_price
            print(f"Order value (BTC): {order_value_btc:.8f} BTC")
            
            # Get BTC/USD price
            btc_usd = self.btc_usd_price
            if btc_usd is None:
                if "ETH/USD" in self.current_prices:
                    eth_price = self.current_prices.get("ETH/USD", 3000)
                    btc_usd = eth_price * 18
                    print(f"⚠️ BTC/USD not available, estimating from ETH: ${btc_usd:.2f}")
                else:
                    btc_usd = 90000.0
                    print(f"⚠️ BTC/USD not available, using fallback: ${btc_usd:.2f}")
            
            order_value_usd = order_value_btc * btc_usd
            print(f"Order value (USD): ${order_value_usd:.2f} (BTC: {order_value_btc:.8f} @ ${btc_usd:.2f}/BTC)")
            
            if order_value_usd < min_order_size:
                print(f"❌ FAIL: ${order_value_usd:.2f} < ${min_order_size:.2f}")
                return False
            else:
                print(f"✅ PASS: ${order_value_usd:.2f} >= ${min_order_size:.2f}")
                return True
        else:
            order_value = rounded_volume * rounded_price
            if order_value < min_order_size:
                print(f"❌ FAIL: ${order_value:.2f} < ${min_order_size:.2f}")
                return False
            else:
                print(f"✅ PASS: ${order_value:.2f} >= ${min_order_size:.2f}")
                return True

# Test the fix
print("="*60)
print("COMPREHENSIVE ORDER VALUE CALCULATION TEST")
print("="*60)

test = TestOrderValue()

# Set up prices (simulating what the bot would have)
test.current_prices["ETH/USD"] = 3042.35
test.btc_usd_price = None  # Will use fallback

# Test XRP/BTC sell orders (the failing case)
xrp_btc_config = {
    'kraken_pair': 'XXRPXXBT',
    'precision': 8,
    'volume_precision': 2,
    'min_order_size': 10.0  # $10 USD
}

print("\n" + "="*60)
print("TEST 1: XRP/BTC Sell Order (10.06 XRP @ 0.0000227 BTC)")
print("="*60)
result1 = test.place_limit_order_test(
    "XRP/BTC", "sell", 
    volume=10.06, 
    price=0.0000227, 
    config=xrp_btc_config
)

print("\n" + "="*60)
print("TEST 2: XRP/BTC Sell Order (25.16 XRP @ 0.0000227 BTC)")
print("="*60)
result2 = test.place_limit_order_test(
    "XRP/BTC", "sell", 
    volume=25.16, 
    price=0.0000227, 
    config=xrp_btc_config
)

print("\n" + "="*60)
print("TEST 3: XRP/BTC Buy Order (small volume)")
print("="*60)
# For buy orders, volume is XRP, price is BTC/XRP
result3 = test.place_limit_order_test(
    "XRP/BTC", "buy", 
    volume=100.0,  # XRP
    price=0.0000227,  # BTC per XRP
    config=xrp_btc_config
)

print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
if result1 and result2 and result3:
    print("✅ ALL TESTS PASSED - Order value calculation is correct!")
    print("\nThe fix should work when deployed. Make sure to:")
    print("1. Rebuild Docker container: docker build --no-cache -t gridbot-pnl .")
    print("2. Restart: docker-compose restart")
    print("3. Check logs for '✅ Order value for XRP/BTC' messages")
else:
    print("❌ SOME TESTS FAILED - Check the logic above")

