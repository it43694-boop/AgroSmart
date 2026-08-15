from pathlib import Path

path = Path(r'c:\Users\ACHANGER\anaconda3\projet2\main.py')
text = path.read_text(encoding='utf-8')
idx = text.find('from services.ml_service import AdvancedMLService')
print('idx', idx)
print(repr(text[idx-30:idx+120]))
idx2 = text.find('# ============= AI & ML Service Endpoints =============')
print('idx2', idx2)
print(repr(text[idx2:idx2+120]))
idx3 = text.find('# Computer Vision Service Endpoints', idx2)
print('idx3', idx3)
print(repr(text[idx3:idx3+120]))
