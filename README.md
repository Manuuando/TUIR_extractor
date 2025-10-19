# TUIR Extractor

This repository now includes a lightweight React front-end to explore the TUIR outline and chat with the QA backend.

## Backend API expectations

The UI assumes the backend exposes the following HTTP endpoints on `http://localhost:8000` (the default target configured for the dev proxy):

- `GET /api/history` &rarr; returns an array of conversation entries with the shape `{ id, question, answer, createdAt }`.
- `POST /api/qa` &rarr; accepts `{ "question": "..." }` and streams back the answer body while optionally returning the conversation id in the `X-Conversation-Id` header.
- `GET /api/documents/outline` (or `/api/outline`) &rarr; returns a JSON array describing the TUIR outline.

> ℹ️ If your backend serves the outline from a static file instead, place it at `frontend/public/tuir_outline.json` or adjust the endpoints in `DocumentExplorer`.

## Front-end setup

```bash
cd frontend
npm install
```

### Available scripts

- `npm run dev` – start the Vite development server (defaults to port `5173`). Requests to `/api/*` are proxied to `http://localhost:8000`.
- `npm run build` – generate a production build under `frontend/dist`.
- `npm run preview` – serve the production build locally after running `npm run build`.

### Running alongside the backend

1. Start the backend in a separate terminal (for example with `uvicorn app.main:app --reload --port 8000`, or the command appropriate for your project).
2. From another terminal launch the front-end development server:

   ```bash
   cd frontend
   npm run dev
   ```

3. Open http://localhost:5173 in your browser. The dev server will proxy API requests to the backend on port 8000 so both services work together during development.

## Building for production

Run `npm run build` to emit the static assets into `frontend/dist`. You can then serve that directory from your preferred web server or integrate it with the backend.
