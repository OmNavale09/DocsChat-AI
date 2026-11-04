# DocChat AI – AI-Powered Document Assistant

An AI-powered document assistant that allows users to upload Word documents (`.docx`), ask questions about their content, and make document edits using natural language.

Built using React.js, Python, Flask, LangChain, Gemini API and ChromaDB.

## Features

- **DOCX Upload:** Upload Word documents and process their content.
- **AI-Powered Q&A:** Ask questions and receive context-aware answers based on the uploaded document.
- **RAG Pipeline:** Uses text chunking, embeddings and vector similarity search to retrieve relevant document content.
- **Document Editing:** Analyze document content and perform requested modifications.
- **Edit Verification:** Verify document content before applying changes.
- **Interactive Interface:** Chat with your document through a React-based interface.

## Tech Stack

| Category            | Technologies          |
|---                  |---                    |
| Frontend            | React.js              |
| Backend             | Python, Flask         |
| LLM Framework       | LangChain             |
| AI Model            | Google Gemini API     |
| Vector Database     | ChromaDB              |
| Embeddings          | Sentence Transformers |
| Document Processing | python-docx, Docx2txt |

## Architecture

DocChat AI uses a Retrieval-Augmented Generation (RAG) architecture to answer questions using the uploaded document.

```text
                  User
                   |
                   v
             React Frontend
                   |
                   v
              Flask Backend
                   |
                   v
             DOCX Processing
                   |
                   v
             Text Extraction
                   |
                   v
              Text Chunking
                   |
                   v
          Generate Embeddings
                   |
                   v
                ChromaDB
                   |
                   v
              User Question
                   |
                   v
           Similarity Search
                   |
                   v
          Relevant Document Chunks
                   |
                   v
              Gemini API
                   |
                   v
             AI Response
                   |
                   v
             React Frontend
```

### Document Editing Workflow

The document editing workflow uses AI-powered analysis and verification to handle modification requests.

1. **Document Analysis:** Understands the requested modification and identifies the relevant document content.
2. **Editing:** Generates the required document changes.
3. **Verification:** Checks the proposed changes before applying them.
4. **Document Modification:** Uses Python document-processing tools to update the DOCX file.

## Project Structure

```text
DocChat-AI/
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── ai-server/
│   ├── app.py
│   ├── edit_tool.py
│   ├── document_analysis_tool.py
│   ├── uploads/
│   └── requirements.txt
│
├── .gitignore
└── README.md
```

*Adjust the folder and file names above if your actual repository structure differs.*

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/OmNavale09/DocsChat-AI.git

cd DocsChat-AI
```

### 2. Backend Setup

Navigate to the AI server directory:

```bash
cd ai-server
```

Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file inside the `ai-server` directory:

```env
GOOGLE_API_KEY=your_gemini_api_key
```

Replace the placeholder with your Google Gemini API key.

### 4. Start the Backend

```bash
python app.py
```

### 5. Frontend Setup

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open the local URL displayed in your terminal.

## Environment Variables

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | API key used to access Google Gemini |

Never commit your `.env` file or expose API keys publicly.

## Future Improvements

- Support for additional document formats.
- Document version history and change tracking.
- Multiple document management.
- Improved document editing and formatting preservation.
- Export and download edited documents.

## Author

**Om Suresh Navale**

- GitHub: [OmNavale09](https://github.com/OmNavale09)
- LinkedIn: [Om Navale](https://www.linkedin.com/in/omnavale/)

---

*DocChat AI – Making document interaction smarter with AI.*
