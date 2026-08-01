"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import { preprocessLaTeX } from "@/lib/latex";

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
            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:underline break-all"
              >
                {children}
              </a>
            );
          },
          // Responsive Images
          img({ src, alt }) {
            return (
              <img
                src={src}
                alt={alt || "Content image"}
                className="max-w-full h-auto rounded-lg border shadow-xs my-2 object-contain"
              />
            );
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}
