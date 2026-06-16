const STYLESHEET_ID = "teg-chatbot-styles";

function findWidgetScript(script: HTMLScriptElement | null): HTMLScriptElement | null {
  if (script?.src) {
    return script;
  }

  const scripts = document.querySelectorAll<HTMLScriptElement>(
    'script[src*="teg-chatbot"]',
  );
  return scripts[scripts.length - 1] ?? null;
}

export function injectWidgetStyles(script: HTMLScriptElement | null) {
  const widgetScript = findWidgetScript(script);
  if (!widgetScript?.src || document.getElementById(STYLESHEET_ID)) {
    return;
  }

  const link = document.createElement("link");
  link.id = STYLESHEET_ID;
  link.rel = "stylesheet";
  link.href = widgetScript.src.replace(/\.js(?:\?.*)?$/, ".css");
  document.head.appendChild(link);
}
