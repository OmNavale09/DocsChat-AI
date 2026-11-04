
from docx import Document
from crewai.tools import tool


def create_document_analysis_tool(file_path):

    @tool("Analyze DOCX Document Structure")
    def get_document_structure() -> str:
        """
        Extract all non-empty paragraphs from the uploaded DOCX document.

        Returns:
            Paragraph indexes, exact paragraph text, and paragraph styles.
            Use these exact indexes and texts when proposing document edits.
        """

        doc = Document(file_path)

        paragraphs = []

        for index, paragraph in enumerate(doc.paragraphs):

            if paragraph.text.strip():

                paragraphs.append({
                    "paragraph_index": index,
                    "text": paragraph.text,
                    "style": paragraph.style.name
                })

        return str(paragraphs)

    return get_document_structure
