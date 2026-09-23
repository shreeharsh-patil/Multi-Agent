from pathlib import Path

path = Path('frontend/src/app/layout.tsx')
text = path.read_text(encoding='utf-8')
text = text.replace('  maximumScale: 1,\n', '')
text = text.replace('  userScalable: false,\n', '')
if 'maximumScale: 1' in text or 'userScalable: false' in text:
    raise RuntimeError('mobile zoom restrictions are still present')
path.write_text(text, encoding='utf-8')
print('mobile viewport zoom restrictions removed')
