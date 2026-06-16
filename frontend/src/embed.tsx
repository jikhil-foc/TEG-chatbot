import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ChatWidget, type ChatWidgetProps } from "@/widget/ChatWidget";
import { injectWidgetStyles } from "@/utils/injectStyles";

export interface TegChatbotInitOptions extends ChatWidgetProps {
  container?: HTMLElement;
}

function readScriptConfig(script: HTMLScriptElement | null): ChatWidgetProps {
  if (!script) {
    return {};
  }

  const { dataset } = script;
  return {
    apiBaseUrl: dataset.apiUrl,
    title: dataset.title,
    subtitle: dataset.subtitle,
    placeholder: dataset.placeholder,
    welcomeMessage: dataset.welcome,
    position: dataset.position === "bottom-left" ? "bottom-left" : "bottom-right",
    primaryColor: dataset.color,
  };
}

export function init(options: TegChatbotInitOptions = {}) {
  const script =
    document.currentScript instanceof HTMLScriptElement
      ? document.currentScript
      : null;

  injectWidgetStyles(script);

  const config = { ...readScriptConfig(script), ...options };
  const container =
    options.container ??
    (() => {
      const existing = document.getElementById("teg-chatbot-root");
      if (existing) {
        return existing;
      }
      const node = document.createElement("div");
      node.id = "teg-chatbot-root";
      document.body.appendChild(node);
      return node;
    })();

  const root = createRoot(container);
  root.render(
    <StrictMode>
      <ChatWidget {...config} />
    </StrictMode>,
  );

  return { destroy: () => root.unmount() };
}

declare global {
  interface Window {
    TegChatbot?: {
      init: typeof init;
    };
  }
}

window.TegChatbot = { init };

if (document.currentScript?.hasAttribute("data-auto-init")) {
  const run = () => init();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run, { once: true });
  } else {
    run();
  }
}
