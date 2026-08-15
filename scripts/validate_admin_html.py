from pathlib import Path
from html.parser import HTMLParser

text = Path('frontend/admin.html').read_text(encoding='utf-8')

class TagChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []
        self.voids = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag not in self.voids:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in self.voids:
            return
        if not self.stack:
            self.errors.append(('unexpected-closing', tag, self.getpos()))
            return
        last, pos = self.stack.pop()
        if last != tag:
            self.errors.append(('mismatch', last, tag, pos, self.getpos()))

    def close(self):
        super().close()
        for tag, pos in self.stack:
            self.errors.append(('unclosed', tag, pos))

checker = TagChecker()
checker.feed(text)
checker.close()
print('errors count', len(checker.errors))
for e in checker.errors[:50]:
    print(e)
