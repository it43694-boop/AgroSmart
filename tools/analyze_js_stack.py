from pathlib import Path
s=Path('tmp_script7.js').read_text(encoding='utf-8')
counts={'{':0,'}':0,'(':0,')':0,'[':0,']':0,'`':0,"'":0,'"':0}
for i,ch in enumerate(s,1):
    if ch in counts:
        counts[ch]+=1
print(counts)
# find last 200 chars
print('tail:\n', s[-200:])
# find last unmatched backtick
bt_count = s.count('`')
print('backtick count', bt_count)
# find open template literal positions naive
positions=[]
for i,ch in enumerate(s):
    if ch=='`': positions.append(i)
print('last 10 backtick positions', positions[-10:])
# simple brace delta scanning
stack=[]
for i,ch in enumerate(s,1):
    if ch in '{([':
        stack.append((ch,i))
    elif ch in '})]':
        if not stack:
            print('extra closing', ch, 'at', i)
            break
        top, pos = stack.pop()
        pairs = {'{':'}','(':')','[':']'}
        if pairs[top]!=ch:
            print('mismatch at',i, top, ch)
            break
else:
    if stack:
        print('unclosed at end, top:', stack[-1])
    else:
        print('all matched')
