
import os
from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from crewai.tools import tool

def create_docx_edit_tool(document_path: str):

    base, ext = os.path.splitext(document_path)
    output_path = f"{base}_edited{ext}"

    current_path = document_path

    @tool
    def edit_docx(
        operation: str,
        paragraph_index: int,
        expected_text: str,
        new_text: str = "",
    ) -> str:
        """
        Apply a verified edit to a paragraph in the DOCX document.

        Args:
            operation: replace, insert_after, or delete.
            paragraph_index: Zero-based paragraph index.
            expected_text: Exact original paragraph text.
            new_text: Replacement or inserted text.
        """

        nonlocal current_path

        if not os.path.isfile(current_path):
            return "ERROR: Document file not found."

        try:
            doc = Document(current_path)
            paragraphs = doc.paragraphs

            if paragraph_index < 0 or paragraph_index >= len(paragraphs):
                return "ERROR: Invalid paragraph index."

            paragraph = paragraphs[paragraph_index]

            if paragraph.text != expected_text:
                return (
                    "REJECTED: Original text does not match. "
                    "No changes were made. Re-analyze the document."
                )

            if operation == "replace":

                # Preserve the first run's formatting where possible.
                if paragraph.runs:
                    paragraph.runs[0].text = new_text

                    for run in paragraph.runs[1:]:
                        run.text = ""
                else:
                    paragraph.add_run(new_text)

            elif operation == "insert_after":

                new_element = OxmlElement("w:p")
                paragraph._p.addnext(new_element)

                new_paragraph = Paragraph(
                    new_element,
                    paragraph._parent
                )

                new_paragraph.add_run(new_text)

            elif operation == "delete":

                paragraph._element.getparent().remove(
                    paragraph._element
                )

            else:
                return "ERROR: Unsupported operation."

            # Save the edited document.
            doc.save(output_path)

            # Verify saved document.
            saved_doc = Document(output_path)

            if operation == "replace":

                if not any(
                    p.text == new_text
                    for p in saved_doc.paragraphs
                ):
                    return "ERROR: Replacement verification failed."

            elif operation == "insert_after":

                if not any(
                    p.text == new_text
                    for p in saved_doc.paragraphs
                ):
                    return "ERROR: Insertion verification failed."

            elif operation == "delete":

                if any(
                    p.text == expected_text
                    for p in saved_doc.paragraphs
                ):
                    return "ERROR: Deletion verification failed."

            current_path = output_path

            return (
                f"SUCCESS: {operation} applied and verified. "
                f"Updated document: {output_path}"
            )

        except Exception as e:
            return f"ERROR: Document editing failed: {str(e)}"

    return edit_docx