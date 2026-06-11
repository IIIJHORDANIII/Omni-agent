import os
import chromadb
from chromadb.utils import embedding_functions
import threading

class SemanticMemory:
    """
    Camada de Memória Semântica usando ChromaDB.
    Transforma fatos e observações em vetores para busca por significado.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized: return
        
        # Caminho para persistência local
        self.db_path = os.path.expanduser("~/Documents/pessoal/agent/memory_db")
        os.makedirs(self.db_path, exist_ok=True)
        
        # Inicializa cliente Chroma
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Usamos um modelo de embedding leve e eficiente (Default do Chroma ou SentenceTransformer)
        # O default do Chroma é o 'all-MiniLM-L6-v2', excelente para o M3.
        self.embed_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Cria ou obtém a coleção principal
        self.collection = self.client.get_or_create_collection(
            name="omniscient_facts",
            embedding_function=self.embed_fn
        )
        
        self._initialized = True
        print("Memória Semântica (ChromaDB) ONLINE.")

    def write(self, key, value, metadata=None):
        """Salva um fato no banco vetorial."""
        print(f"RAG: Indexando '{key}'...")
        try:
            self.collection.upsert(
                ids=[key],
                documents=[value],
                metadatas=[metadata or {"type": "fact"}]
            )
            return True
        except Exception as e:
            print(f"Erro ao escrever na memória semântica: {e}")
            return False

    def query(self, text, n_results=3):
        """Busca os fatos mais relevantes baseados no significado do texto."""
        try:
            results = self.collection.query(
                query_texts=[text],
                n_results=n_results
            )
            # Retorna uma lista de strings (documentos)
            if results and 'documents' in results and results['documents']:
                return results['documents'][0]
            return []
        except Exception as e:
            print(f"Erro na busca semântica: {e}")
            return []

    def get_context_for_prompt(self, query):
        """Retorna um bloco de texto formatado com os fatos recuperados para injetar no prompt."""
        relevant_facts = self.query(query)
        if not relevant_facts: return ""
        
        context = "\n--- MEMÓRIAS RELEVANTES RECUPERADAS ---\n"
        for i, fact in enumerate(relevant_facts, 1):
            context += f"{i}. {fact}\n"
        context += "---------------------------------------\n"
        return context
