import os
import PyPDF2
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

DB_DIR = "src/data/chroma_db"
DOCS_DIR = "src/data/docs"

def extract_text_from_pdfs(pdf_paths):
    text = ""
    for path in pdf_paths:
        try:
            with open(path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n\n"
        except Exception as e:
            print(f"Error reading {path}: {e}")
    return text

def process_documents(api_key):
    os.environ["GOOGLE_API_KEY"] = api_key
    
    # 1. Get all PDFs
    if not os.path.exists(DOCS_DIR):
        return False, "Diretório de documentos não encontrado."
        
    pdf_files = [os.path.join(DOCS_DIR, f) for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]
    if not pdf_files:
        return False, "Nenhum PDF encontrado para processar."
        
    # 2. Extract Text
    raw_text = extract_text_from_pdfs(pdf_files)
    if not raw_text.strip():
         return False, "Não foi possível extrair texto dos PDFs."
    
    # 3. Split Text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(raw_text)
    
    # 4. Create Embeddings and Save to Chroma
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    # GARANTIA DE CRIAÇÃO DA PASTA (A proteção está aqui!)
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Clear old vector DB if it exists (for fresh updates)
    if os.path.exists(DB_DIR):
        import shutil
        try:
            shutil.rmtree(DB_DIR)
        except Exception as e:
            print(f"Aviso ao limpar pasta: {e}")
        
    vectorstore = Chroma.from_texts(
        texts=chunks, 
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    
    return True, "Base de conhecimento atualizada com sucesso!"

def get_vectorstore(api_key):
    os.environ["GOOGLE_API_KEY"] = api_key
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    if os.path.exists(DB_DIR):
        return Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    return None
