/** Map server response language names to short display codes. */
export function formatResponseLanguageCode(
  language: string | null | undefined,
): string | null {
  if (!language) {
    return null;
  }

  const normalized = language.trim().toLowerCase();

  if (normalized === "english" || normalized === "en") {
    return "EN";
  }

  if (normalized === "irish" || normalized === "ga" || normalized === "gaeilge") {
    return "GA";
  }

  return null;
}
