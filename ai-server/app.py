from flask import Flask,request,jsonify,send_file
from flask_cors import CORS

import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from langchain.tools import tool 
from langchain.agents import create_agent
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import InMemorySaver

from langchain_community.document_loaders import Docx2txtLoader
from werkzeug.utils import secure_filename
from uuid import uuid4

from crewai import Agent, LLM, Process, Task, Crew 
from edit_tool import create_docx_edit_tool
from document_analysis_tool import create_document_analysis_tool

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

checkpointer = InMemorySaver()
config = {"configurable": {"thread_id": "1"}}

UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def update_vector_store(file_path, doc_id):

    # Remove previous chunks belonging to this document
    vector_store.delete(
        where={"doc_id": doc_id}
    )

    # Load updated DOCX
    loader = Docx2txtLoader(file_path)
    docs = loader.load()

    # Split document into chunks
    splits = text_splitter.split_documents(docs)

    # Add document metadata
    for split in splits:
        split.metadata["doc_id"] = doc_id
        split.metadata["original_filename"] = os.path.basename(file_path)

    # Store updated chunks
    if splits:
        vector_store.add_documents(
            documents=splits,
            ids=[str(uuid4()) for _ in splits]
        )

    return len(splits)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    add_start_index=True,
)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)

vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",
)

ACTIVE_DOC_ID = None
uploaded_docx_path = None

model = init_chat_model(
    "google_genai:gemini-2.5-flash",
    api_key=GOOGLE_API_KEY,
)

@tool
def retrieve_from_pdf(query: str) -> str:
    """Retrieve information from the currently uploaded DOCX document."""

    if not ACTIVE_DOC_ID:
        return "No document has been uploaded."

    documents = vector_store.similarity_search(
        query,
        k=5,
        filter={"doc_id": ACTIVE_DOC_ID}
    )

    content = ""

    for doc in documents:
        content += f"""
        Metadata: {doc.metadata}
        Content: {doc.page_content}
        """

    return content if content else "No relevant information found."

web_search_tool = TavilySearch(
    max_results=5,
    search_depth="advanced",
    tavily_api_key=TAVILY_API_KEY,
)

system_prompt = """You are a helpful research assistant with access to two tools:
1. retrieve_from_pdf: Use this to find information from the
   docx file provided by user
2. TavilySearch: Use this to find current information
   not in the docx provided by the user (recent events, updates, etc.)

Strategy:
- For questions about the docx file content → use retrieve_from_pdf
- For questions about recent events or topics not in the docx file -> use web_search_tool"""

agent = create_agent(
    model = model,
    tools = [retrieve_from_pdf, web_search_tool],
    system_prompt = system_prompt,
    checkpointer=checkpointer
)

##crew ------------------
def create_edit_crew(file_path):
    # Load document content
    loader = Docx2txtLoader(file_path)
    docs = loader.load()

    document_content = "\n".join(
        doc.page_content for doc in docs
    )

    # Define output path
    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_edited{ext}"

    # Create editing tool
    docx_edit_tool = create_docx_edit_tool(file_path)

    docx_edit_tool = create_docx_edit_tool(file_path)
    llm = LLM(
       model="gemini/gemini-3.5-flash-lite",
       api_key=GOOGLE_API_KEY
    )

    analysis_tool = create_document_analysis_tool(file_path)

    document_analyzer = Agent(
    role="Document Analysis Specialist",
    goal="Understand the user's editing request and identify the exact "
         "document content and locations that need to be changed.",
    backstory=(
        "You are a document analysis specialist skilled at understanding "
        "the structure, meaning, and context of DOCX documents. "
        "You locate relevant paragraphs and sections, interpret the user's "
        "intent, and provide precise references to the content that needs editing."
    ),
    verbose=True,
    llm=llm,
    tools=[analysis_tool]
)

    document_editor = Agent(
    role="Document Editing Specialist",
    goal="Create accurate, context-aware edits that satisfy the user's "
         "request while preserving the document's original meaning and style.",
    backstory=(
        "You are an expert document editor. You transform editing instructions "
        "into precise proposed changes using the analysis provided to you. "
        "You preserve relevant context, maintain consistency, and avoid "
        "unrequested changes. You propose edits rather than modifying files directly."
    ),
    verbose=True,
    llm=llm,
)

    document_verifier = Agent(
    role="Document Verification and Quality Assurance Specialist",
    goal="Verify proposed document edits against the user's request and use "
         "approved tools to apply valid changes to the actual DOCX document.",
    backstory=(
        "You are a meticulous document quality assurance specialist. "
        "You check whether proposed edits match the user's intent, preserve "
        "unrelated content, and target the correct document locations. "
        "You reject incorrect or ambiguous edits and use document editing "
        "tools to apply verified changes. You confirm the resulting document "
        "content after editing."
    ),
    verbose=True,
    llm=llm,
    tools=[docx_edit_tool]
)

    task_analyze = Task(
        description=(
            "Analyze the user's document editing request: {user_request}\n\n"

            "DOCUMENT STRUCTURE:\n"
            f"{document_content}\n\n"

            "Instructions:\n"
            "1. Understand the user's requested changes.\n"
            "2. Identify the exact paragraph indexes.\n"
            "3. Copy the COMPLETE original paragraph text.\n"
            "4. Explain the context of each target paragraph.\n"
            "5. Never invent paragraph indexes or text.\n"
            "6. If the target is ambiguous, report the ambiguity.\n\n"

            "Output each target using:\n"
            "- Paragraph Index:\n"
            "- Exact Original Text:\n"
            "- Context:\n"
        ),
        expected_output=(
            "A structured analysis containing exact paragraph indexes "
            "and complete original paragraph text."
        ),
        agent=document_analyzer,
    )
 
    task_edit = Task(
    description=(
        "Create proposed edits based on the user's request: {user_request}\n"
        "Use the document analysis provided by the previous task.\n"
        "1. Create the exact replacement, insertion, or deletion required.\n"
        "2. Preserve the original meaning and relevant writing style.\n"
        "3. Avoid unrelated changes.\n"
        "4. Include the original text and proposed new text for each edit.\n"
        "5. Assign a unique ID to each proposed edit.\n"
        "Do not modify the actual document.\n"
        "Output format:\n"
        "## Proposed Document Edits\n"
        "- Edit ID: ...\n"
        "- Operation: Replace / Insert / Delete\n"
        "- Target: ...\n"
        "- Original Text: ...\n"
        "- Proposed Text: ...\n"
        "- Reason: ..."
    ),
    expected_output="A structured list of proposed edits with unique IDs, target locations, and original and proposed text.",
    agent=document_editor,
    context=[task_analyze],
)

    task_verify = Task(
    description=(
        "Verify the proposed document edits against the user's request: {user_request}\n"
        "Use the document analysis and proposed edits from the previous tasks.\n"
        "1. Verify that each edit satisfies the user's intent.\n"
        "2. Check that the target location and original text match the document.\n"
        "3. Reject edits that are incorrect, ambiguous, or unrelated.\n"
        "4. Use the available document editing tools to apply only verified edits.\n"
        "5. Read the edited content back and verify that the changes were applied correctly.\n"
        "6. Report any failed edits without claiming they were successful.\n"
        "Output format:\n"
        "## Document Edit Verification\n"
        "- Edit ID: ...\n"
        "- Verification: Approved / Rejected\n"
        "- Applied: Yes / No\n"
        "- Verification Result: ...\n"
        "- Errors: ..."
        """IMPORTANT TOOL INSTRUCTIONS:

The edit_docx tool accepts these parameters:

- operation: "replace", "insert_after", or "delete"
- paragraph_index: Zero-based paragraph index.
- expected_text: Exact original paragraph text.
- new_text: Replacement or inserted text.

Rules:

1. Always use the exact paragraph_index from the analysis.
2. Always provide the complete original paragraph as expected_text.
3. Never invent paragraph indexes or original text.
4. If the tool rejects an edit, do not retry with guessed values.
5. Only report an edit as successful if the tool returns SUCCESS.
6. Apply replacements before structural changes.
7. Apply structural changes in descending paragraph_index order."""
    ),
    expected_output="A verification report listing approved, rejected, successfully applied, and failed edits.",
    agent=document_verifier,
    context=[task_analyze, task_edit],
)

    edit_crew = Crew(
    agents=[document_analyzer, document_editor, document_verifier],
    tasks=[task_analyze, task_edit, task_verify],
    process= Process.sequential 
)
    return edit_crew, document_content, output_path

app = Flask(__name__)
CORS(app)

@app.route("/upload-docx", methods=["POST"])
def upload_docx():
    global ACTIVE_DOC_ID, uploaded_docx_path, config
    config = {
        "configurable": {
            "thread_id": str(uuid4())
        }
    }

    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not file.filename.lower().endswith(".docx"):
            return jsonify({"error": "Only DOCX files are supported"}), 400

        # Generate a unique document ID
        doc_id = str(uuid4())

        filename = secure_filename(file.filename)

        # Save file
        saved_filename = f"{doc_id}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)

        file.save(file_path)

        # Load DOCX
        loader = Docx2txtLoader(file_path)
        docs = loader.load()

        if not docs or not any(doc.page_content.strip() for doc in docs):
            os.remove(file_path)
            return jsonify({"error": "Document is empty"}), 400

        # Split document
        splits = text_splitter.split_documents(docs)

        # Attach metadata to every chunk
        for split in splits:
            split.metadata["doc_id"] = doc_id
            split.metadata["original_filename"] = filename

        # Store in ChromaDB
        vector_store.add_documents(
            documents=splits,
            ids=[str(uuid4()) for _ in splits]
        )

        # Set currently active document
        ACTIVE_DOC_ID = doc_id
        uploaded_docx_path = file_path

        return jsonify({
            "message": "Document uploaded and indexed successfully",
            "document_id": doc_id,
            "filename": filename,
            "total_chunks": len(splits)
        }), 200

    except Exception as e:
        print("Upload error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()

        message = data.get("message")

        if not message:
            return jsonify({"error": "Message is required"}), 400

        if not ACTIVE_DOC_ID:
            return jsonify({"error": "Please upload a DOCX first"}), 400

        response = agent.invoke(
            {
                "messages": [
                    {"role": "user", "content": message}
                ]
            },
            config=config
        )

        content = response["messages"][-1].content 
        if isinstance(content, list):
            answer = "\n".join(
            block.get("text", "")
            for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        else:
            answer = content
        
        print(answer)

        return jsonify({
            "answer": answer
        }), 200

    except Exception as e:
        print("Chat error:", str(e))

        return jsonify({
            "error": str(e)
        }), 500

@app.route("/edit-docx", methods=["POST"])
def edit_docx():

    global uploaded_docx_path

    try:
        # 1. Get user request
        data = request.get_json(silent=True) or {}

        user_request = data.get("user_request", "").strip()

        if not user_request:
            return jsonify({
                "error": "Editing request is required"
            }), 400

        # 2. Check uploaded document
        if not uploaded_docx_path or not os.path.exists(uploaded_docx_path):
            return jsonify({
                "error": "Please upload a DOCX first"
            }), 400

        if not ACTIVE_DOC_ID:
            return jsonify({
                "error": "No active document found"
            }), 400

        # 3. Create editing crew
        edit_crew, document_content, output_path = create_edit_crew(
            uploaded_docx_path
        )

        # 4. Remove previous output if it exists
        if os.path.exists(output_path):
            os.remove(output_path)

        # 5. Execute crew
        result = edit_crew.kickoff(
            inputs={
                "user_request": user_request,
                "document_content": document_content
            }
        )

        print("\nEDIT CREW RESULT:")
        print(result)

        # 6. Check generated document
        if not os.path.exists(output_path):
            return jsonify({
                "error": "No edited document was generated.",
                "report": str(result)
            }), 500

        # 7. Update active document
        uploaded_docx_path = output_path

        # 8. Re-index updated document
        updated_chunks = update_vector_store(
            uploaded_docx_path,
            ACTIVE_DOC_ID
        )

        print(f"Updated Chunks: {updated_chunks}")

        # 9. Return edited DOCX
        return send_file(
            uploaded_docx_path,
            as_attachment=True,
            download_name="edited_document.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:

        print("Edit error:", str(e))

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)