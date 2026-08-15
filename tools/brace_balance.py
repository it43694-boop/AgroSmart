from pathlib import Path
s=Path('tmp_script7.js').read_text(encoding='utf-8')
lines=s.splitlines()
stack=[]
pairs={'}':'{',']':'[',')':'('}
for lineno,line in enumerate(lines, start=1):
    for ch in line:
        if ch in '{([':
            stack.append((ch, lineno))
        elif ch in '})]':
            if stack and stack[-1][0]==pairs[ch]:
                stack.pop()
            else:
                print('mismatch', ch, 'at', lineno)
                stack.append(('?', lineno))
    # print stack size occasionally
    if lineno % 50 == 0:
        print('line', lineno, 'stack', len(stack))
# After scanning
print('END stack size', len(stack))
if stack:
    print('top unclosed', stack[-1])
    print('show last 10 stack entries:')
    for e in stack[-10:]:
        print(e)
    # show lines around last unclosed
    last_line = stack[-1][1]
    for i in range(max(1,last_line-5), min(len(lines), last_line+5)):
        print(i+1, lines[i])
