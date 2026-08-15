import sys
sys.path.insert(0, r"c:\Users\ACHANGER\anaconda3\projet2")
try:
    import routers.modules_router as m
    print('Imported modules_router OK')
    print('ai_router:', getattr(m, 'ai_router', None))
except Exception as e:
    import traceback
    traceback.print_exc()
