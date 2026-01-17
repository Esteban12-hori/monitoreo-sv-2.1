try:
    import pysnmp
    print(f"pysnmp imported: {pysnmp.__file__}")
    from pysnmp.hlapi import *
    print("pysnmp.hlapi imported")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
