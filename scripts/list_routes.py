import sys
sys.path.insert(0, r"c:\Users\ACHANGER\anaconda3\projet2")
try:
    import main
    routes = sorted({r.path for r in main.app.routes if hasattr(r,'path')})
    for r in routes:
        print(r)
except Exception:
    import traceback
    traceback.print_exc()
