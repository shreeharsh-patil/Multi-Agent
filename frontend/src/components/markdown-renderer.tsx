"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import { preprocessLaTeX } from "@/lib/latex";
import { downloadSecureFile } from "@/lib/download";
import { ImagePreviewCard } from "@/components/image-preview-card";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
const resolveApiUrl = (url?: string) => url?.startsWith('/api/') ? `${BACKEND_URL}${url}` : url;

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  const processedContent = preprocessLaTeX(content);

  return (
    <div className={`prose dark:prose-invert max-w-full overflow-x-hidden text-sm leading-relaxed ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, [remarkMath, { singleDollar: true }]]}
        rehypePlugins={[rehypeKatex, rehypeRaw]}
        components={{
          // Responsive Table Wrapper
          table({ children }) {
            return (
              <div className="table-responsive my-4 border rounded-lg overflow-x-auto max-w-full">
                <table className="w-full text-left border-collapse text-xs sm:text-sm">
                  {children}
                </table>
              </div>
            );
          },
          // Responsive Code & Pre blocks
          pre({ children }) {
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
            return (
              <code className="font-mono text-xs sm:text-sm" {...props}>
                {children}
              </code>
            );
          },
          // Responsive Math / Formula Container
          div({ className, children, ...props }) {
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
          a({ href, children }) {
            const resolved = resolveApiUrl(href);
            const textContent = typeof children === 'string' ? children.toLowerCase() : '';
            const isDownload = resolved?.includes('/download') || textContent.includes('download');
            if (isDownload && resolved) {
              return (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    downloadSecureFile(resolved, 'downloaded-file');
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
          img({ src, alt }) {
            if (typeof src !== 'string') return null;
            const resolvedSrc = resolveApiUrl(src) || src;
            return <ImagePreviewCard src={resolvedSrc} alt={alt || 'Generated image'} />;
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}
