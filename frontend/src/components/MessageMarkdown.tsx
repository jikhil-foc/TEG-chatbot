import { useMemo } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Source } from "@/types";
import {
  buildCitationSourceMap,
  citationIndexFromHref,
  isCitationHref,
  linkifyCitations,
} from "@/utils/citations";
import { CitationPopover } from "./CitationPopover";

interface MessageMarkdownProps {
  content: string;
  sources?: Source[];
}

export function MessageMarkdown({ content, sources }: MessageMarkdownProps) {
  const citationMap = useMemo(
    () =>
      sources && sources.length > 0
        ? buildCitationSourceMap(content, sources)
        : new Map<number, Source>(),
    [content, sources],
  );

  const markdown = useMemo(
    () => linkifyCitations(content, citationMap),
    [content, citationMap],
  );

  return (
    <div className="teg-markdown">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            if (isCitationHref(href)) {
              const index = citationIndexFromHref(href ?? "");
              const source = citationMap.get(index);
              if (source) {
                return <CitationPopover index={index} source={source} />;
              }
            }

            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {markdown}
      </Markdown>
    </div>
  );
}
