from pathlib import Path

source_path = Path('.github/scripts/apply_streaming_repair_v3.py')
source = source_path.read_text(encoding='utf-8')
old = "    helper = '''\n\nasync def _synthesize_draft_stream"
new = "    helper = r'''\n\nasync def _synthesize_draft_stream"
if old not in source:
    raise RuntimeError('Could not locate synthesis helper literal in v3 patcher')
source = source.replace(old, new, 1)
exec(compile(source, str(source_path), 'exec'))
