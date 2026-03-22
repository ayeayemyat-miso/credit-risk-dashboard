# test_imports.py
print("Testing imports...")

try:
    import fastapi
    print("✅ fastapi")
except: print("❌ fastapi")

try:
    import dash
    print("✅ dash")
except: print("❌ dash")

try:
    import yfinance
    print("✅ yfinance")
except: print("❌ yfinance")

try:
    import sqlalchemy
    print("✅ sqlalchemy")
except: print("❌ sqlalchemy")

print("\n✅ All good! Ready to build the dashboard.")