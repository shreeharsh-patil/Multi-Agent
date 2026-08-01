/**
 * Production-ready LaTeX and Markdown preprocessor.
 *
 * Handles:
 * 1. Preserving code blocks (``` ... ``` and ` ... `) untouched.
 * 2. Unescaping double backslashes before LaTeX syntax (e.g. \\tau -> \tau, \\frac -> \frac, \\begin -> \begin).
 * 3. Normalizing LaTeX delimiters: \( ... \) to $ ... $, \[ ... \] to $$ ... $$.
 * 4. Auto-wrapping unwrapped \begin{...} ... \end{...} blocks in $$ ... $$.
 * 5. Ensuring block equations ($$ ... $$) are surrounded by empty lines so remark-math parses them reliably.
 */
export function preprocessLaTeX(content: string): string {
  if (!content) return "";

  // 1. Separate code blocks to avoid altering LaTeX inside fenced/inline code blocks
  const codeBlocks: string[] = [];
  let processed = content.replace(/(```[\s\S]*?```|`[^`\n]+`)/g, (match) => {
    codeBlocks.push(match);
    return `___CODE_BLOCK_${codeBlocks.length - 1}___`;
  });

  // 2. Unescape double backslashes before LaTeX commands: e.g. \\frac -> \frac, \\tau -> \tau, \\begin -> \begin
  processed = processed.replace(/\\\\([a-zA-Z]+|\\|\{|\})/g, "\\$1");

  // 3. Convert \( ... \) to $ ... $ (inline math) and \[ ... \] to $$ ... $$ (block math)
  processed = processed.replace(/\\\(([\s\S]*?)\\\)/g, (_, math) => `$${math.trim()}$`);
  processed = processed.replace(/\\\[([\s\S]*?)\\\]/g, (_, math) => `\n\n$$\n${math.trim()}\n$$\n\n`);

  // 4. Auto-wrap unwrapped \begin{env} ... \end{env} environments in block $$ ... $$
  processed = processed.replace(
    /(?<!\$\$[\s\S]*?)(\\begin\{(?:equation|align|matrix|pmatrix|bmatrix|vmatrix|cases|array)\*?\}[\s\S]*?\\end\{(?:equation|align|matrix|pmatrix|bmatrix|vmatrix|cases|array)\*?\})/g,
    (match) => `\n\n$$\n${match.trim()}\n$$\n\n`
  );

  // 5. Ensure $$ ... $$ display equations have proper newlines for remark-math parsing
  processed = processed.replace(/\$\$\s*([\s\S]*?)\s*\$\$/g, (_, math) => `\n\n$$\n${math.trim()}\n$$\n\n`);

  // 6. Restore preserved code blocks
  processed = processed.replace(/___CODE_BLOCK_(\d+)___/g, (_, index) => {
    return codeBlocks[parseInt(index, 10)] || "";
  });

  return processed;
}
