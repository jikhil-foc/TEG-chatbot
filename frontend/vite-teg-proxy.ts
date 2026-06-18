const PROXY_PREFIX = "/teg-site";

const REWRITABLE_CONTENT_TYPES = [
  "text/html",
  "text/css",
  "application/javascript",
  "text/javascript",
  "application/json",
];

export function shouldRewriteContent(contentType: string | undefined): boolean {
  if (!contentType) {
    return false;
  }

  const lower = contentType.toLowerCase();
  return REWRITABLE_CONTENT_TYPES.some((type) => lower.includes(type));
}

export function rewriteTegContent(body: string, contentType: string): string {
  let output = body
    .replace(/https?:\/\/www\.teg\.ie/gi, PROXY_PREFIX)
    .replace(/https?:\/\/teg\.ie/gi, PROXY_PREFIX)
    .replace(/\/\/www\.teg\.ie/gi, PROXY_PREFIX);

  const lower = contentType.toLowerCase();

  if (lower.includes("text/html")) {
    if (!/<base\s/i.test(output)) {
      output = output.replace(
        /<head(\s[^>]*)?>/i,
        (match) => `${match}<base href="${PROXY_PREFIX}/">`,
      );
    }

    output = output.replace(
      /(\s(?:href|src|action)\s*=\s*["'])\/(?!teg-site\b)/gi,
      `$1${PROXY_PREFIX}/`,
    );
  }

  if (lower.includes("text/css")) {
    output = output.replace(
      /url\(\s*(['"]?)\/(?!teg-site\b)/gi,
      `url($1${PROXY_PREFIX}/`,
    );
  }

  return output;
}

export function rewriteLocationHeader(
  location: string | undefined,
): string | undefined {
  if (!location) {
    return location;
  }

  return location
    .replace(/^https?:\/\/www\.teg\.ie/i, PROXY_PREFIX)
    .replace(/^https?:\/\/teg\.ie/i, PROXY_PREFIX);
}

export function stripFrameBlockingHeaders(
  headers: Record<string, string | string[] | undefined>,
): void {
  delete headers["x-frame-options"];
  delete headers["content-security-policy"];
  delete headers["content-security-policy-report-only"];
}
