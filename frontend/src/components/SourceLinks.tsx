import type { Source } from "@/types";

interface SourceLinksProps {
  sources: Source[];
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
                className="teg-sources__link"
              >
                {source.title || source.url}
              </a>
            ) : (
              <span>{source.title || source.chunk_id}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
