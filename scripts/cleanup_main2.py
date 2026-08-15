from pathlib import Path

path = Path(__file__).resolve().parent.parent / 'main.py'
text = path.read_text(encoding='utf-8')
lines = text.replace('\r\n', '\n').split('\n')

# Remove duplicate vision import block, leaving only one.
vision_block = [
    'try:',
    '',
    '    from services.computer_vision_service import PlantDiseaseDiagnostician',
    '',
    'except Exception as e:',
    '',
    '    PlantDiseaseDiagnostician = None',
    '',
    '    print(f"Vision service import skipped: {e}")',
]

match_indices = []
for idx in range(len(lines) - len(vision_block) + 1):
    if lines[idx:idx+len(vision_block)] == vision_block:
        match_indices.append(idx)

if len(match_indices) > 1:
    # drop all but the first occurrence
    for idx in reversed(match_indices[1:]):
        del lines[idx:idx+len(vision_block)]

# Remove stale AdvancedMLService init block and keep only PlantDiseaseDiagnostician init.
start_marker = '# Initialiser les services IA'
plant_block_start = None
for idx, line in enumerate(lines):
    if line.strip() == start_marker:
        plant_block_start = idx
        break

if plant_block_start is not None:
    # find the start of the plant diagnostician try block after the stale ML block
    target_line = '    if PlantDiseaseDiagnostician is not None:'
    plant_try_idx = None
    for idx in range(plant_block_start + 1, len(lines)):
        if lines[idx] == target_line and idx > plant_block_start:
            # ensure it is preceded by a 'try:' line somewhere above
            if idx >= 1 and lines[idx-1].strip() == '':
                for back in range(idx-3, plant_block_start - 1, -1):
                    if lines[back].strip() == 'try:':
                        plant_try_idx = back
                        break
            if plant_try_idx is not None:
                break

    if plant_try_idx is not None:
        # rebuild the block
        prefix = lines[:plant_block_start]
        suffix = lines[plant_try_idx:]
        replacement = [
            '# Initialiser les services IA',
            '',
            'plant_diagnostician = None',
            '',
            'multilingual_chatbot = None',
            '',
            'report_generator = None',
            '',
            '',
        ]
        lines = prefix + replacement + suffix

new_text = '\r\n'.join(lines)
path.write_text(new_text, encoding='utf-8')
print('cleanup_main2 completed')
