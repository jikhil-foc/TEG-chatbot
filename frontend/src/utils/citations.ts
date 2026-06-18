import type { Source } from "@/types";

const CITATION_RE = /\[(\d+)\]/g;
const CITATION_LINK_PREFIX = "#teg-cite-";

/** Map citation numbers in answer order to their cited sources. */
export function buildCitationSourceMap(
  content: string,
  sources: Source[],
): Map<number, Source> {
  const map = new Map<number, Source>();
  const seen = new Set<number>();
  let sourceIndex = 0;

  for (const match of content.matchAll(CITATION_RE)) {
    const citationIndex = Number.parseInt(match[1], 10);
    if (seen.has(citationIndex)) {
      continue;
    }
    seen.add(citationIndex);
    if (sourceIndex < sources.length) {
      map.set(citationIndex, sources[sourceIndex]);
      sourceIndex += 1;
    }
  }

  return map;
}

/** Turn ``[2]`` markers into markdown links when a matching source exists. */
export function linkifyCitations(
  content: string,
  citationMap: Map<number, Source>,
): string {
  if (citationMap.size === 0) {
    return content;
  }

  return content.replace(CITATION_RE, (match, indexText: string) => {
    const citationIndex = Number.parseInt(indexText, 10);
    if (!citationMap.has(citationIndex)) {
      return match;
    }
    return `[${citationIndex}](${CITATION_LINK_PREFIX}${citationIndex})`;
  });
}

export function isCitationHref(href: string | undefined): boolean {
  return href?.startsWith(CITATION_LINK_PREFIX) ?? false;
}

export function citationIndexFromHref(href: string): number {
  return Number.parseInt(href.slice(CITATION_LINK_PREFIX.length), 10);
}
