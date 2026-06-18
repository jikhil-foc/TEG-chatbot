import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ChatWidget } from "@/widget/ChatWidget";
import "@/styles/demo.css";

const tegSiteUrl = import.meta.env.DEV ? "/teg-site/" : "https://www.teg.ie/";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <div className="demo-page">
      <iframe
        className="demo-page__site"
        src={tegSiteUrl}
        title="TEG – Teastas Eorpach na Gaeilge"
        referrerPolicy="no-referrer-when-downgrade"
      />
      <ChatWidget />
    </div>
  </StrictMode>,
);
