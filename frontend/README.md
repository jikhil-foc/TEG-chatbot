# TEG Chatbot Widget

Embeddable React chat widget for the TEG Chatbot API. Connects to `POST /api/v1/ask` (Server-Sent Events) for streamed RAG-backed answers with source citations.

## Setup

```bash
cd frontend
npm install
```

Ensure the FastAPI backend is running on port 8000:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Development

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). API calls to `/api/v1/*` are proxied to `http://localhost:8000`.

## Build

```bash
# Demo app + embeddable widget bundle
npm run build

# Widget bundle only (outputs dist/widget/teg-chatbot.js)
npm run build:widget
```

## Embed on any website

After building, host `dist/widget/teg-chatbot.js` and `dist/widget/teg-chatbot.css` together on your CDN or static server. The script auto-loads the stylesheet from the same path.

```html
<script
  src="https://your-cdn.example/teg-chatbot.js"
  data-auto-init
  data-api-url="https://api.example.com"
  data-title="TEG Assistant"
  data-subtitle="Ask about TEG levels and exams"
  data-welcome="Hello! How can I help you today?"
  data-position="bottom-right"
  data-color="#9fc74a"
></script>
```

### Script data attributes

| Attribute | Description |
|-----------|-------------|
| `data-api-url` | Base URL of the TEG Chatbot API (required in production) |
| `data-title` | Panel header title |
| `data-subtitle` | Panel header subtitle |
| `data-placeholder` | Input placeholder text |
| `data-welcome` | Initial assistant welcome message |
| `data-position` | `bottom-right` (default) or `bottom-left` |
| `data-color` | Primary brand color (CSS hex) |
| `data-auto-init` | Auto-mount the widget when the script loads |

### Programmatic init

```html
<script src="https://your-cdn.example/teg-chatbot.js"></script>
<script>
  window.TegChatbot.init({
    apiBaseUrl: "https://api.example.com",
    title: "TEG Assistant",
    position: "bottom-left",
  });
</script>
```

## React import

```tsx
import { ChatWidget } from "./widget/ChatWidget";

<ChatWidget apiBaseUrl="http://localhost:8000" />;
```
