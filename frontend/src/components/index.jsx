
import React, { useState } from 'react';
import mammoth from 'mammoth/mammoth.browser';
import './index.css';
import DocxViewer from './docs';
const API_URL = "http://localhost:5000";

export default function ChatWithDocsApp() {
  const [documents, setDocuments] = useState([]);
  const [isChatting, setIsChatting] = useState(false);
  const [activeDocId, setActiveDocId] = useState(null);
  const [inputMode, setInputMode] = useState("chat");
  console.log(inputMode)
  const [messages, setMessages] = useState([
    {
      sender: 'ai',
      text: 'Hello! Upload a Word document to view it page by page and chat with it.',
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isParsing, setIsParsing] = useState(false);

  const activeDoc = documents.find((doc) => doc.id === activeDocId);

  const handleFileUpload = async (e) => {
  const file = e.target.files?.[0];

  if (!file) return;

  setIsParsing(true);

  try {
    if (!file.name.toLowerCase().endsWith(".docx")) {
      throw new Error("Only .docx files are supported.");
    }

    // 1. Upload DOCX to Flask backend
    const formData = new FormData();
    formData.append("file", file);

    const uploadResponse = await fetch(`${API_URL}/upload-docx`, {
      method: "POST",
      body: formData,
    });

    const uploadData = await uploadResponse.json();

    if (!uploadResponse.ok) {
      throw new Error(uploadData.error || "Upload failed.");
    }

    // 2. Extract text for frontend viewer
    const result = await mammoth.extractRawText({
      arrayBuffer: await file.arrayBuffer(),
    });

    const baseDoc = {
      id: uploadData.document_id,
      name: uploadData.filename,
      size: (file.size / 1024).toFixed(1) + " KB",
      uploadDate: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      file,
      content: result.value.trim(),
      error: "",
    };

    if (!baseDoc.content) {
      baseDoc.error = "No readable text found.";
    }

    // 3. Update frontend
    setDocuments([baseDoc]);
    setActiveDocId(uploadData.document_id);

    // 4. Reset previous chat
    setMessages([
      {
        sender: "ai",
        text: `Successfully uploaded "${uploadData.filename}". You can now ask questions about your document.`,
      },
    ]);

  } catch (error) {
    console.error("Upload failed:", error);

    setMessages((prev) => [
      ...prev,
      {
        sender: "ai",
        text: `Upload failed: ${error.message}`,
      },
    ]);

  } finally {
    setIsParsing(false);
    e.target.value = "";
  }
};

const handleSendMessage = async (event) => {
  event.preventDefault()
  const message = inputMessage.trim();

  if (!message || isChatting) return;

  setInputMessage("");
  setIsChatting(true);

  // Show user message
  setMessages((prev) => [
    ...prev,
    {
      sender: "user",
      text: message,
    },
  ]);

  try {
    if (inputMode === "chat") {
      // CHAT MODE
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Chat failed");
      }

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: data.answer,
        },
      ]);
    } else {
      // EDIT MODE
      const response = await fetch(`${API_URL}/edit-docx`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_request: message,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || "Document editing failed");
      }

      // Backend returns the edited DOCX file
      const blob = await response.blob();

      const editedFile = new File(
        [blob],
        "edited_document.docx",
        {
          type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
      );

      // Update document preview
      setDocuments((prev) =>
        prev.map((doc) =>
          doc.id === activeDocId
            ? { ...doc, file: editedFile }
            : doc
        )
      );

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: "Your document has been edited successfully!",
        },
      ]);

      // Download edited document
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "edited_document.docx";
      link.click();
      URL.revokeObjectURL(url);
    }
  } catch (error) {
    setMessages((prev) => [
      ...prev,
      {
        sender: "ai",
        text: `Error: ${error.message}`,
      },
    ]);
  } finally {
    setIsChatting(false);
  }
};

  const handleDeleteDoc = (e, id) => {
    e.stopPropagation();

    const remaining = documents.filter((doc) => doc.id !== id);
    setDocuments(remaining);

    if (activeDocId === id) {
      setActiveDocId(remaining.length ? remaining[0].id : null);
    }
  };

  return (
    <div className="cwd-app-container">
      <aside className="cwd-sidebar">
        <div className="cwd-logo-area">
          <div className="cwd-logo-icon">📄</div>
          <div className="cwd-logo-title">
            <h2>DocChat AI</h2>
            <span>Document Reader & Assistant</span>
          </div>
        </div>

        {documents.length > 0 && (
          <div className="cwd-doc-list-section">
            <span className="section-title">YOUR DOCUMENTS</span>

            <div className="cwd-doc-list">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className={`cwd-doc-item ${
                    activeDocId === doc.id ? 'active' : ''
                  }`}
                  onClick={() => setActiveDocId(doc.id)}
                >
                  <span className="doc-icon">📑</span>

                  <div className="doc-details">
                    <span className="doc-name">{doc.name}</span>
                    <span className="doc-meta">{doc.size}</span>
                  </div>

                  <button
                    type="button"
                    className="doc-delete"
                    onClick={(e) => handleDeleteDoc(e, doc.id)}
                    title="Remove document"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="cwd-sidebar-chatbox">
          <div className="cwd-chat-header">
            <h3>Chat Assistant</h3>
            {activeDoc && (
              <span className="active-tag">
                Active: {activeDoc.name}
              </span>
            )}
          </div>

          <div className="cwd-chat-messages">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`cwd-message ${msg.sender}`}
              >
                <p>{msg.text}</p>
              </div>
            ))}
          </div>

<form
            className="cwd-chat-input-form"
            onSubmit={handleSendMessage}
          >
<div className="flex gap-2 mb-3">
  <button
    type="button"
    onClick={() => setInputMode("chat")}
    className={`px-4 py-2 rounded-lg ${
      inputMode === "chat"
        ? "bg-blue-600 text-white"
        : "bg-gray-200 text-gray-700"
    }`}
  >
    Chat
  </button>

  <button
    type="button"
    onClick={() => setInputMode("edit")}
    className={`px-4 py-2 rounded-lg ${
      inputMode === "edit"
        ? "bg-blue-600 text-white"
        : "bg-gray-200 text-gray-700"
    }`}
  >
    Edit Document
  </button>
</div>
<input
  type="text"
  value={inputMessage}
  onChange={(e) => setInputMessage(e.target.value)}
  placeholder={
    inputMode === "chat"
      ? "Ask anything about your document..."
      : "Describe what you want to change..."
  }
  disabled={isChatting}
/>
            <button type="submit">{isChatting ? "Thinking..." : "Send"}</button>
          </form>

        </div>
      </aside>

      <main className="cwd-main-container">
        <header className="cwd-main-header">
          <div className="header-info">
            <h1>{activeDoc ? activeDoc.name : 'Document Viewer'}</h1>
            <p>
              {activeDoc
                ? `Uploaded at ${activeDoc.uploadDate} • ${activeDoc.size}`
                : 'Upload a .docx document to view it page by page.'}
            </p>
          </div>

          <label htmlFor="file-upload" className="cwd-upload-btn">
            <span>
              {isParsing ? 'Processing...' : '+ Upload .docx'}
            </span>

            <input
              id="file-upload"
              type="file"
              accept=".docx"
              multiple
              onChange={handleFileUpload}
              disabled={isParsing}
              style={{ display: 'none' }}
            />
          </label>
        </header>

        <div className="cwd-reader-container">
          {activeDoc ? (
            <div className="cwd-paper">
              <div className="cwd-paper-header">
                <span className="paper-title">
                  {activeDoc.name}
                </span>
                <span className="paper-badge">READ MODE</span>
              </div>

              <div className="cwd-paper-body">
                <DocxViewer
                  key={activeDoc.id}
                  file={activeDoc.file}
                />
              </div>
            </div>
          ) : (
            <div className="cwd-empty-reader">
              <div className="empty-icon">📂</div>
              <h2>No Document Opened</h2>
              <p>
                Upload a .docx file to view its formatted pages here.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
