from pathlib import Path

path = Path('backend/src/api/routes/chat.py')
text = path.read_text(encoding='utf-8')
old = '''    needs_full_runtime = bool(re.search(
        r"(?i)\\b(?:research|latest|current|search|calculate|calendar|drive|file|pdf|web|"
        r"image|weather|news|price|stock|crypto|email|gmail|contact|task|schedule|"
        r"code|debug|python|javascript|typescript|medical|health|finance)\\b",
        body.message,
    ))
'''
new = '''    needs_full_runtime = bool(re.search(
        r"(?ix)(?:"
        r"\\b(?:research|latest|current|calculate|calendar|drive|file|pdf|web|"
        r"image|weather|news|price|stock|crypto|email|gmail|contact|task|schedule|"
        r"code|debug|python|javascript|typescript|medical|health|finance)\\b|"
        r"\\bsearch\\s+(?:the\\s+)?(?:web|internet|google)\\b|"
        r"\\bweb\\s+search\\b|\\blook\\s+up\\b|\\bfind\\s+online\\b"
        r")",
        body.message,
    ))
'''
if new in text:
    print('already applied')
elif old not in text:
    raise RuntimeError('expected fast routing guard not found')
else:
    path.write_text(text.replace(old, new, 1), encoding='utf-8')
    print('refined fast routing guard')
