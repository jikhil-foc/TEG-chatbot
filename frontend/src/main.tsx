import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ChatWidget } from "@/widget/ChatWidget";
import "@/styles/demo.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <div className="demo-page">
      <header className="demo-page__hero">
        <p className="demo-page__eyebrow">TEG Chatbot</p>
        <h1>Embedded widget demo</h1>
        <p>
          Use the chat button in the corner to ask questions. In development,
          requests are proxied to <code>http://localhost:8000</code>.
        </p>
      </header>
      <ChatWidget />
    </div>
  </StrictMode>,
);
