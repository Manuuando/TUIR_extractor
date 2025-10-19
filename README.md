# TUIR Extractor

A fully local question-answering stack for the Italian **Testo Unico delle Imposte sui Redditi (TUIR)**. The project downloads the
official TUIR document, builds a vector index with free embedding models, and serves a FastAPI backend that streams answers from a
locally hosted transformer. A React front-end lets you explore the document outline and review previous questions.

> ✅ Everything runs on your machine. No paid or third-party API keys are required once the models and the PDF are cached locally.

---

## Table of contents

1. [Features](#features)
2. [Architecture overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Step-by-step setup on Windows 11 with VS Code](#step-by-step-setup-on-windows-11-with-vs-code)
   - [1. Install tooling](#1-install-tooling)
   - [2. Clone the repository](#2-clone-the-repository)
   - [3. Create and activate the Python virtual environment](#3-create-and-activate-the-python-virtual-environment)
   - [4. Install Python dependencies](#4-install-python-dependencies)
   - [5. Create the environment file](#5-create-the-environment-file)
   - [6. Download and index the TUIR](#6-download-and-index-the-tuir)
   - [7. Start the FastAPI backend](#7-start-the-fastapi-backend)
   - [8. Install front-end dependencies](#8-install-front-end-dependencies)
   - [9. Launch the React dev server](#9-launch-the-react-dev-server)
   - [10. Explore the application](#10-explore-the-application)
5. [Backend API reference](#backend-api-reference)
6. [Environment variables](#environment-variables)
7. [Project structure](#project-structure)
8. [Running tests](#running-tests)
9. [Regenerating data & maintenance tasks](#regenerating-data--maintenance-tasks)
10. [Troubleshooting tips](#troubleshooting-tips)

---

## Features

- 📄 **Automatic ingestion** – downloads the official TUIR PDF and splits it into article-sized sections.
- 🔍 **Semantic retrieval** – builds a FAISS index with `sentence-transformers/all-MiniLM-L6-v2` for fast, local similarity search.
- 🧠 **Local language model** – streams answers using a transformer such as `tiiuae/falcon-7b-instruct` with zero external API calls.
- 🗂️ **Document explorer** – browse a generated outline of the TUIR from the web interface.
- 💬 **Conversation history** – each answer is persisted locally and can be revisited from the UI.

## Architecture overview

```
backend/
├── app.py          # FastAPI application with retrieval + answer endpoints
├── ingest.py       # PDF downloader, parser, embedding generation, outline builder
├── history.py      # JSON-based persistence for chat history
└── data/           # Generated assets: tuir.pdf, FAISS index, metadata, histories
frontend/
├── src/App.tsx     # React entry point combining explorer + chat + history
└── ...             # Components, styles, and Vite configuration
```

The front-end communicates with the backend over HTTP. During development, Vite proxies `/api/*` requests to `http://localhost:8000`.

## Prerequisites

Install the following software on Windows 11 before starting:

| Tool | Minimum version | Notes |
| ---- | ---------------- | ----- |
| [Python](https://www.python.org/downloads/windows/) | 3.10 | Make sure "Add Python to PATH" is selected during installation. |
| [Node.js](https://nodejs.org/en/download/prebuilt-installer) | 18 LTS or newer | Includes `npm`. |
| [Git](https://git-scm.com/download/win) | Latest | Required for cloning the repository. |
| [Visual Studio Code](https://code.visualstudio.com/) | Latest | Optional but recommended for development. |
| [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) | — | Needed if `pip` compiles wheels (FAISS, torch). |

> 💡 **GPU acceleration** is optional. If you have a CUDA-capable GPU, install the matching GPU build of PyTorch following the
> [official instructions](https://pytorch.org/get-started/locally/).

## Step-by-step setup on Windows 11 with VS Code

All commands below assume you are using **PowerShell**. If script execution is restricted, enable it once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
```

### 1. Install tooling

Install Python, Node.js, Git, and VS Code using the links above. After installation, restart PowerShell and verify the versions:

```powershell
python --version
npm --version
git --version
code --version
```

### 2. Clone the repository

Open VS Code, press **Ctrl+Shift+P**, run **Git: Clone**, and enter the repository URL. Alternatively, use PowerShell:

```powershell
cd $HOME\source
git clone https://github.com/<your-account>/TUIR_extractor.git
cd TUIR_extractor
```

### 3. Create and activate the Python virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

The prompt should now show `(.venv)` indicating the environment is active. VS Code usually picks it up automatically (check the
status bar in the bottom-right corner).

### 4. Install Python dependencies

Inside the activated environment, install the backend requirements:

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

> ⏱️ The first installation can take a while because `torch`, `transformers`, and `sentence-transformers` download sizeable wheels.

### 5. Create the environment file

1. Copy the sample file:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Open `.env` in VS Code and adjust values if needed. Default values already point to public resources and safe defaults:

   ```env
   TUIR_SOURCE_URL=https://www1.finanze.gov.it/upload/tuir.pdf
   TUIR_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   TUIR_LLM_MODEL=tiiuae/falcon-7b-instruct
   TUIR_LOCAL_ONLY=1
   TUIR_MAX_NEW_TOKENS=512
   TUIR_TEMPERATURE=0.2
   ```

   Keeping `TUIR_LOCAL_ONLY=1` guarantees the backend uses only locally cached models.

### 6. Download and index the TUIR

Run the ingestion pipeline once to download the PDF, extract its text, compute embeddings, and generate the outline:

```powershell
python -m backend.ingest
```

You should see logs indicating the download, extraction, and FAISS index creation. Generated assets appear under `backend/data/`:

- `tuir.pdf`
- `tuir.faiss`
- `tuir_metadata.json`
- `tuir_outline.json`

### 7. Start the FastAPI backend

With the virtual environment still active:

```powershell
uvicorn backend.app:app --reload --port 8000
```

The API exposes streaming answers and serves history/outline endpoints. Leave this terminal open while the server runs.

### 8. Install front-end dependencies

Open a **new** PowerShell window, navigate to the project, and install the Node packages:

```powershell
cd $HOME\source\TUIR_extractor\frontend
npm install
```

### 9. Launch the React dev server

```powershell
npm run dev
```

Vite starts on <http://localhost:5173>. API calls to `/api/*` are proxied to the FastAPI server on port `8000`.

### 10. Explore the application

1. Open <http://localhost:5173> in your browser.
2. Use the **Document Explorer** to browse the automatically generated TUIR outline.
3. Ask questions in the **Chat Panel**. Answers stream in real time, and a new conversation entry appears in the history sidebar.

> 📝 Each prompt/answer pair is stored under `backend/data/history/`. Removing a file clears that conversation from the history list.

## Running tests

The backend includes a small automated suite powered by **pytest**. After installing the Python dependencies and activating your virtual environment, run the tests from the project root:

```powershell
pytest
```

The configuration lives in `pyproject.toml`, so no additional flags are required. Use `python -m pytest` if your shell does not expose the `pytest` entry point.

## Backend API reference

| Method & Path | Description |
| ------------- | ----------- |
| `GET /api/health` | Service heartbeat (also available at `/health`). |
| `POST /query` | Retrieve the top matching sections for a question (JSON body `{ "question": "...", "top_k": 5 }`). |
| `POST /api/qa` | Stream an answer. Accepts `{ "question": "...", "session_id": "optional", "top_k": 5, "max_new_tokens": 512, "temperature": 0.2 }`. Returns plain-text tokens and sets `X-Conversation-Id`. |
| `POST /answer` | Legacy alias of `/api/qa`. |
| `GET /api/history` | List stored conversations: `[{ id, question, answer, createdAt }]`. |
| `GET /api/history/{session_id}` | Retrieve the detailed message log for one conversation. |
| `DELETE /api/history/{session_id}` | Remove a stored conversation. |
| `GET /api/outline` | Download the generated document outline (also under `/api/documents/outline`). |

## Environment variables

Environment variables can be set in the `.env` file at the project root. They are loaded automatically when the backend starts.

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `TUIR_SOURCE_URL` | Public URL for the TUIR PDF. | `https://www1.finanze.gov.it/upload/tuir.pdf` |
| `TUIR_EMBEDDING_MODEL` | Sentence-transformer used for vector embeddings. | `sentence-transformers/all-MiniLM-L6-v2` |
| `TUIR_LLM_MODEL` | Hugging Face model name or local path for answer generation. | `tiiuae/falcon-7b-instruct` |
| `TUIR_LOCAL_ONLY` | When `1`, forces Hugging Face loaders to use cached/local files only. | `1` |
| `TUIR_MAX_NEW_TOKENS` | Default maximum tokens generated per answer. | `512` |
| `TUIR_TEMPERATURE` | Sampling temperature for generation (`0` disables randomness). | `0.2` |

Override them by editing `.env` or by exporting environment variables before starting the backend.

## Project structure

```
TUIR_extractor/
├── backend/
│   ├── app.py
│   ├── data/
│   ├── history.py
│   └── ingest.py
├── frontend/
│   ├── src/
│   └── vite.config.ts
├── requirements.txt
├── package.json (front-end inside ./frontend)
├── .env.example
└── README.md
```

## Regenerating data & maintenance tasks

- **Rebuild the FAISS index / outline**: delete `backend/data/tuir.faiss`, `backend/data/tuir_metadata.json`, and `backend/data/tuir_outline.json`, then rerun `python -m backend.ingest`.
- **Force a PDF redownload**: run `python -m backend.ingest --force` by editing the script or set `TUIR_SOURCE_URL` to a new mirror and delete the existing `tuir.pdf`.
- **Clear chat history**: remove JSON files under `backend/data/history/` or call `DELETE /api/history/{session_id}`.
- **Production front-end build**: from `frontend/`, execute `npm run build` and serve the `frontend/dist` directory (e.g., with `npm run preview`).
- **Run the backend without auto-reload**: `uvicorn backend.app:app --host 0.0.0.0 --port 8000`.

## Troubleshooting tips

- **Missing build tools**: If `pip install` fails while compiling native extensions, install the *Microsoft C++ Build Tools* and rerun the installation.
- **Large model downloads**: Some transformer models are several GB. Download them beforehand with `huggingface-cli download` if you plan to work offline.
- **CUDA errors**: Ensure the CUDA toolkit version matches the PyTorch build you installed. Alternatively, use the CPU wheel by reinstalling PyTorch without CUDA.
- **Port conflicts**: If port `8000` or `5173` is in use, adjust them via `uvicorn --port <new>` and `npm run dev -- --port <new>` and update the proxy in `frontend/vite.config.ts` accordingly.
- **Slow ingestion**: PDF parsing can take several minutes. The log output provides progress; reruns are fast once the assets are cached.

Happy hacking! 🛠️
