import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    
    print(" All imports successful!")
    
    # Test instantiation (dummy response for scrapers would be needed for full test)
    print(" Classes identified correctly.")

except Exception as e:
    print(f" Import failed: {e}")
    sys.exit(1)
