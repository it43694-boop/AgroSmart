from pathlib import Path
s=Path('tmp_script7.js').read_text(encoding='utf-8')
pos=53250
start=max(0,pos-200)
end=min(len(s), pos+200)
context=s[start:end]
# compute line number
line_num = s.count('\n',0,pos)+1
print('line', line_num, 'char pos', pos)
print('-----context start-----')
print(context)
print('-----context end-----')
# print surrounding lines with numbers
lines = s.splitlines()
ln = line_num
for i in range(max(0,ln-6), min(len(lines), ln+6)):
    print(f'{i+1:6}: {lines[i]}')
