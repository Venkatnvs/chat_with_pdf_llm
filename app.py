import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import logging
import asyncio

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def pdf_to_text_convert(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def text_to_chunks(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=1000)
    chunks = splitter.split_text(text)
    return chunks

def convert_text_to_embeddings_vectors(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

def main_chat_chain():
    prompt_template = """
    You are an AI assistant with access to the contents of a PDF document. Your task is to answer the question based on the provided context.
    
    Context: {context}
    
    Question: {question}
    
    Answer in a clear and concise manner. If the answer is not present in the context, reply with "The answer is not available in the provided context."
    """
    
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    
    return chain

async def user_input(user_question):
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        docs = new_db.similarity_search(user_question)
        chain = main_chat_chain()

        response = await asyncio.to_thread(chain, {"input_documents": docs, "question": user_question}, return_only_outputs=True)
        st.write("Reply:")
        st.write(response["output_text"])
    except Exception as e:
        logging.error("Error during user input processing: %s", str(e))
        st.error("An error occurred while processing your request. Please check the logs for more details.")

def main():
    st.set_page_config(page_title="Chat PDF")
    st.header("Chat with PDF using Gemini💁")

    user_question = st.text_input("Ask a Question from the PDF Files")

    if user_question:
        asyncio.run(user_input(user_question))

    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button", accept_multiple_files=True)
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                try:
                    raw_text = pdf_to_text_convert(pdf_docs)
                    text_chunks = text_to_chunks(raw_text)
                    convert_text_to_embeddings_vectors(text_chunks)
                    st.success("Done")
                except Exception as e:
                    logging.error("Error during PDF processing: %s", str(e))
                    st.error("An error occurred during processing. Please check the logs for more details.")

if __name__ == "__main__":
    main()
