import json
import os
import sys

# Ensure the project root is on sys.path so sibling modules can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import mali_apis

res = mali_apis.MaliRealAPIs.get_mali_market_prices()
# Normalize for readable output
out = {}
if isinstance(res, dict):
    for k, v in res.items():
        if isinstance(v, dict):
            out[k] = {"price": v.get('price'), 'unit': v.get('unit'), 'source': v.get('source'), 'market': v.get('market')}
        else:
            out[k] = v

print(json.dumps(out, ensure_ascii=False, indent=2))
