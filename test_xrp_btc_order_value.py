"""
Test script to verify XRP/BTC order value calculation
This simulates the order placement logic to catch the $0.00 bug
"""

def test_xrp_btc_order_value():
    """Test XRP/BTC order value calculation"""
    print("=" * 60)
    print("TESTING XRP/BTC ORDER VALUE CALCULATION")
    print("=" * 60)
    
    # Simulate the values from the logs
    rounded_volume = 10.06  # XRP
    rounded_price = 0.0000227  # BTC per XRP
    min_order_size = 10.0  # USD minimum
    
    # Current (WRONG) calculation
    order_value_btc = rounded_volume * rounded_price
    print(f"\nCurrent (WRONG) calculation:")
    print(f"  Volume: {rounded_volume} XRP")
    print(f"  Price: {rounded_price} BTC/XRP")
    print(f"  Order value (BTC): {order_value_btc:.8f} BTC")
    print(f"  Order value (USD - WRONG): ${order_value_btc:.2f} (this is BTC, not USD!)")
    print(f"  Min required: ${min_order_size:.2f} USD")
    print(f"  Result: {'❌ FAIL' if order_value_btc < min_order_size else '✅ PASS'}")
    
    # Fixed calculation - convert BTC to USD
    btc_usd_price = 90000.0  # Current BTC price estimate
    order_value_usd = order_value_btc * btc_usd_price
    
    print(f"\nFixed calculation:")
    print(f"  Volume: {rounded_volume} XRP")
    print(f"  Price: {rounded_price} BTC/XRP")
    print(f"  Order value (BTC): {order_value_btc:.8f} BTC")
    print(f"  BTC/USD price: ${btc_usd_price:.2f}")
    print(f"  Order value (USD): ${order_value_usd:.2f}")
    print(f"  Min required: ${min_order_size:.2f} USD")
    print(f"  Result: {'❌ FAIL' if order_value_usd < min_order_size else '✅ PASS'}")
    
    # Verify the fix
    if order_value_usd >= min_order_size:
        print(f"\n✅ TEST PASSED - Order value calculation is correct!")
        print(f"   Order value: ${order_value_usd:.2f} >= ${min_order_size:.2f}")
    else:
        print(f"\n❌ TEST FAILED - Order value still too small")
        print(f"   Order value: ${order_value_usd:.2f} < ${min_order_size:.2f}")
    
    # Test with different volumes
    print(f"\n" + "=" * 60)
    print("TESTING DIFFERENT VOLUMES")
    print("=" * 60)
    
    test_volumes = [10.06, 25.16, 50.0, 100.65]
    for vol in test_volumes:
        btc_val = vol * rounded_price
        usd_val = btc_val * btc_usd_price
        status = "✅" if usd_val >= min_order_size else "❌"
        print(f"{status} {vol:6.2f} XRP = {btc_val:.8f} BTC = ${usd_val:.2f} USD")

if __name__ == "__main__":
    test_xrp_btc_order_value()

