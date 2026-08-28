"use client";

import React, { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { preprocessLaTeX } from "@/lib/latex";
import { downloadSecureFile } from "@/lib/download";
import { ImagePreviewCard } from "@/components/image-preview-card";
import { MermaidWorkspace } from "@/components/mermaid-workspace";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
const resolveApiUrl = (url?: string) => url?.startsWith('/api/') ? `${BACKEND_URL}${url}` : url;

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer = React.memo(function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  const processedContent = useMemo(() => preprocessLaTeX(content), [content]);

  const components = useMemo(() => ({
    // Premium Responsive Markdown Table Rendering
    table: ({ children }: any) => (
      <div className="my-4 w-full max-w-full overflow-x-auto rounded-xl border border-border/80 bg-card/60 shadow-sm backdrop-blur-sm scrollbar-thin">
        <table className="w-full text-left text-xs sm:text-sm border-collapse min-w-[480px]">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }: any) => (
      <thead className="bg-muted/70 text-foreground font-semibold border-b border-border/80">
        {children}
      </thead>
    ),
    tbody: ({ children }: any) => (
      <tbody className="divide-y divide-border/40 text-foreground/90">
        {children}
      </tbody>
    ),
    tr: ({ children }: any) => (
      <tr className="hover:bg-muted/40 transition-colors duration-150">
        {children}
      </tr>
    ),
    th: ({ children }: any) => (
      <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/40 border-r border-border/30 last:border-r-0">
        {children}
      </th>
    ),
    td: ({ children }: any) => (
      <td className="px-4 py-3 align-top border-r border-border/20 last:border-r-0 leading-relaxed font-normal">
        {children}
      </td>
    ),
    // Responsive Code & Pre blocks
    pre({ children }: any) {
      return (
        <div className="code-block-wrapper my-3 bg-card border rounded-lg p-3 max-w-full overflow-x-auto font-mono text-xs sm:text-sm text-foreground">
          <pre className="whitespace-pre overflow-x-auto">{children}</pre>
        </div>
      );
    },
    code({ inline, className, children, ...props }: any) {
      if (inline) {
        return (
          <code className="bg-muted/40 text-primary px-1.5 py-0.5 rounded text-[13px] font-mono break-all max-w-full" {...props}>
            {children}
          </code>
        );
      }
      if (className?.includes("language-mermaid")) {
        const source = String(children).replace(/\n$/, "");
        return <MermaidWorkspace content={`\`\`\`mermaid\n${source}\n\`\`\``} title="Diagram" />;
      }
      return (
        <code className="font-mono text-xs sm:text-sm" {...props}>
          {children}
        </code>
      );
    },
    // Responsive Math / Formula Container
    div({ className, children, ...props }: any) {
      if (className?.includes("math") || className?.includes("katex-display")) {
        return (
          <div className="math-display my-3 max-w-full overflow-x-auto scrollbar-thin text-center py-2 bg-muted/10 rounded-lg" {...props}>
            {children}
          </div>
        );
      }
      return <div className={className} {...props}>{children}</div>;
    },
    // Responsive Link & Word Wrap
    a({ href, children }: any) {
      const resolved = resolveApiUrl(href);
      const textContent = typeof children === 'string' ? children.toLowerCase() : '';
      const isDownload = resolved?.includes('/download') || textContent.includes('download') || resolved?.toLowerCase().endsWith('.pdf');
      if (isDownload && resolved) {
        return (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              downloadSecureFile(resolved);
            }}
            className="text-primary underline hover:underline break-all font-medium cursor-pointer inline-flex items-center gap-1"
          >
            {children}
          </button>
        );
      }
      return (
        <a
          href={resolved}
          target="_blank"
          rel="noreferrer"
          className="text-primary hover:underline break-all"
        >
          {children}
        </a>
      );
    },
    // Responsive ChatGPT Style Image Preview
    img({ src, alt }: any) {
      if (typeof src !== 'string') return null;
      const resolvedSrc = resolveApiUrl(src) || src;
      return <ImagePreviewCard src={resolvedSrc} alt={alt || 'Generated image'} />;
    },
  }), []);

  return (
    <div className={`prose min-w-0 max-w-full break-words text-sm leading-relaxed [overflow-wrap:anywhere] dark:prose-invert ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, [remarkMath, { singleDollar: true }]]}
        rehypePlugins={[rehypeKatex]}
        components={components}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
});
