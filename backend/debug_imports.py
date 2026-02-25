import sys
import os
sys.path.append(os.getcwd())

print("Attempting to import models...")
try:
    from app.models.models import Message
    print("Successfully imported models.")
    print(f"Message fields: {Message.__fields__.keys()}")
except Exception as e:
    print(f"Failed to import models: {e}")
    import traceback
    traceback.print_exc()
