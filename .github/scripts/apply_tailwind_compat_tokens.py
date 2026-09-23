from pathlib import Path

path = Path('frontend/tailwind.config.ts')
text = path.read_text(encoding='utf-8')
old = """    extend: {\n      fontFamily: {"""
new = """    extend: {\n      // Compatibility tokens used throughout the existing UI. These names are\n      // first-class in newer Tailwind/shadcn stacks but need explicit values\n      // while this app remains on Tailwind CSS v3.\n      spacing: {\n        '4.5': '1.125rem',\n      },\n      fontSize: {\n        '4.5xl': ['2.75rem', { lineHeight: '1' }],\n      },\n      boxShadow: {\n        xs: '0 1px 2px 0 rgb(0 0 0 / 0.05)',\n      },\n      transitionDuration: {\n        '350': '350ms',\n      },\n      backdropBlur: {\n        xs: '2px',\n      },\n      fontFamily: {"""
if new in text:
    print('Tailwind compatibility tokens already applied')
elif old in text:
    path.write_text(text.replace(old, new, 1), encoding='utf-8')
    print('Tailwind compatibility tokens applied')
else:
    raise RuntimeError('Could not find Tailwind extend block')
