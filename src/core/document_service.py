import os

class DocumentService:
    def __init__(self):
        pass

    def read_document(self, file_path):
        """Lê o conteúdo de documentos (txt, pdf, docx)."""
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".txt":
                with open(file_path, 'r') as f:
                    return f.read()
            elif ext == ".pdf":
                import pymupdf
                doc = pymupdf.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                return text
            elif ext == ".docx":
                import docx2txt
                return docx2txt.process(file_path)
            else:
                return "Formato de documento não suportado."
        except Exception as e:
            return f"Erro ao ler documento: {str(e)}"
