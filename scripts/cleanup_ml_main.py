from pathlib import Path

path = Path(r'c:\Users\ACHANGER\anaconda3\projet2\main.py')
text = path.read_text(encoding='utf-8')
# Replace the legacy ML import block with the vision service import block.
ml_import_start = text.find('try:\n\n    from services.ml_service import AdvancedMLService')
if ml_import_start == -1:
    raise RuntimeError('Legacy ML import block not found')
ml_import_end = text.find('print(f"ML service import skipped: {e}")', ml_import_start)
if ml_import_end == -1:
    raise RuntimeError('Legacy ML import tail not found')
ml_import_end = text.find('\n\n', ml_import_end)
if ml_import_end == -1:
    ml_import_end = text.find('try:\n\n    from services.computer_vision_service', ml_import_start)
else:
    ml_import_end += 2
legacy_block = text[ml_import_start:ml_import_end]
vision_block = ('try:\n\n'
                '    from services.computer_vision_service import PlantDiseaseDiagnostician\n\n'
                'except Exception as e:\n\n'
                '    PlantDiseaseDiagnostician = None\n\n'
                '    print(f"Vision service import skipped: {e}")\n\n')
text = text.replace(legacy_block, vision_block, 1)
# Remove the in-file ML endpoint section.
start = text.find('# ============= AI & ML Service Endpoints =============')
if start == -1:
    raise RuntimeError('AI section header not found')
end = text.find('# Computer Vision Service Endpoints', start)
if end == -1:
    raise RuntimeError('Computer Vision section header not found')
text = text[:start] + text[end:]
path.write_text(text, encoding='utf-8')
print('patched')
