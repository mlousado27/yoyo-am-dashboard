"""Headless smoke test: runs app.py through Streamlit's AppTest and exercises
the interactive widgets, failing loudly on any exception."""
import sys
from streamlit.testing.v1 import AppTest

def check(at, label):
    if at.exception:
        print(f"[FAIL] {label}")
        for e in at.exception:
            print("   ", repr(e.value) if hasattr(e, "value") else e)
        sys.exit(1)
    print(f"[ok] {label}  (tabs={len(at.tabs)}, toggles={len(at.toggle)}, radios={len(at.radio)})")

at = AppTest.from_file("app.py", default_timeout=90).run()
check(at, "initial load")

# toggle every toggle both ways
for i in range(len(at.toggle)):
    at.toggle[i].set_value(True).run(); check(at, f"toggle[{i}]=True")
    at.toggle[i].set_value(False).run(); check(at, f"toggle[{i}]=False")

# every radio option
for i in range(len(at.radio)):
    for opt in at.radio[i].options:
        at.radio[i].set_value(opt).run(); check(at, f"radio[{i}]={opt}")

print("\nALL CHECKS PASSED")
