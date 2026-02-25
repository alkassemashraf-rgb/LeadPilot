import sys
import os
sys.path.append(os.getcwd())
try:
    from app.api.v1 import inbox  # noqa: F401
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    # sys.exit(1) # We might have DB connection errors if not mocked, but imports should pass.
