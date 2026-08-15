from pathlib import Path
import re
html=Path('frontend/admin.html').read_text(encoding='utf-8')
scripts=re.findall(r'<script\b[^>]*>([\s\S]*?)</script>', html, re.IGNORECASE)
print('found', len(scripts), 'scripts')
script = scripts[7]
Path('tmp_script7_fixed.js').write_text(script, encoding='utf-8')
print('wrote tmp_script7_fixed.js, len', len(script))
