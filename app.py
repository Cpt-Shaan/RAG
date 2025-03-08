import os
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from docx import Document
from tempfile import NamedTemporaryFile

# Set API key
os.environ["GROQ_API_KEY"] = "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"  # Replace with your actual key

def load_document(file):
    """Loads text from a PDF or DOCX file."""
    if file.name.endswith(".pdf"):
        doc_loader = PyPDFLoader(file.name)
        pages = doc_loader.load()
        return "\n".join([page.page_content for page in pages])
    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    return None

def process_text(text):
    """Splits text into chunks and creates embeddings."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50, length_function=len, is_separator_regex=False
    )
    chunks = text_splitter.create_documents([text])
    
    # Embeddings
    model_name = "BAAI/bge-small-en"
    embeddings = HuggingFaceBgeEmbeddings(model_name=model_name)
    
    chunk_texts = [chunk.page_content for chunk in chunks]
    embedding_vectors = embeddings.embed_documents(chunk_texts)
    
    db = FAISS.from_texts(chunk_texts, embeddings)
    return db

def generate_response(db, query):
    """Retrieves relevant chunks and generates response using Groq API."""
    contexts = db.similarity_search(query, k=5)
    
    # Construct prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert at answering questions based on the extracted document context: {context}"),
        ("human", "{question}"),
    ])
    
    model = ChatGroq(model_name="llama3-8b-8192")
    chain = prompt | model
    
    response = chain.invoke({
        "context": "\n\n".join([c.page_content for c in contexts]),
        "question": query
    })
    return response.content

# Streamlit UI
st.title("RAG-based Document Query System")

uploaded_file = st.file_uploader("Upload a PDF or DOCX document", type=["pdf", "docx"])
query = st.text_input("Enter your query:")

if uploaded_file and query:
    with NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(uploaded_file.read())
        temp_file_path = temp_file.name
    
    document_text = load_document(open(temp_file_path, "rb"))
    if document_text:
        db = process_text(document_text)
        response = generate_response(db, query)
        st.subheader("Response:")
        st.write(response)
    else:
        st.error("Unsupported file format.")
