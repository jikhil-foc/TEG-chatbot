import type { Source } from "@/types";

interface SourceLinksProps {
  sources: Source[];
}

function ExternalLinkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M14 3h7v7M10 14 21 3M21 14v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function SourceLinks({ sources }: SourceLinksProps) {
  const visible = sources.filter((source) => source.url || source.title);
  if (visible.length === 0) {
    return null;
  }

  return (
    <div className="teg-sources" aria-label="Sources">
      <p className="teg-sources__label">Sources</p>
      <ul className="teg-sources__list">
        {visible.map((source) => (
          <li key={source.chunk_id}>
            {source.url ? (
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="teg-sources__chip"
              >
                <span className="teg-sources__chip-text">
                  {source.title || source.url}
                </span>
                <ExternalLinkIcon />
              </a>
            ) : (
              <span className="teg-sources__chip teg-sources__chip--static">
                {source.title || source.chunk_id}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
