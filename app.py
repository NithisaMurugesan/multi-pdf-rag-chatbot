import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.memory import ConversationBufferMemory
from htmlTemplates import css,bot_template,user_template
from langchain_classic.chains import ConversationalRetrievalChain # allows us to chat with our context and hold memory of it
from langchain_groq import ChatGroq
from PIL import Image

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text 

def get_text_chunks(raw_text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(raw_text)
    return chunks 

def get_vectorstores(text_chunks):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_texts(
        texts=text_chunks, 
        embedding=embeddings)
    return vectorstore

def get_conversation_chain(vectorstore):
    llm = ChatGroq(
        model_name="llama-3.3-70b-versatile",
        temperature=0
    )
    memory = ConversationBufferMemory(
        memory_key='chat_history', 
        return_messages=True
    )
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 3}
    )
    conversation_chain = ConversationalRetrievalChain.from_llm(
                llm = llm,
                retriever = retriever,
                memory = memory
                )   
    
    return conversation_chain

def handle_userinput(user_question):
    response = st.session_state.conversation.invoke(
        {"question": user_question}
    )   
    st.session_state.chat_history = response['chat_history']
    bot_avatar = Image.open("botpic.jpg")
    user_avatar = Image.open("userpic.png")

    for i,message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            with st.chat_message("user", avatar =user_avatar):
                st.write(message.content)
        else:
            with st.chat_message("assistant", avatar=bot_avatar):
                st.write(message.content)


def main():
    load_dotenv()
    st.set_page_config(page_title = "Chat with multiple PDFs", page_icon = ":books:")

    if "conversation" not in st.session_state:
        st.session_state.conversation = None # Incase if the text is already implemented this allows us to check and set the text to None to avoid reimplimentation

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    st.header("Chat with multiple PDFs :books:")
    user_question = st.text_input("Ask a question about your document:")
    if user_question:
        if st.session_state.conversation:
            handle_userinput(user_question)
        else:
            st.warning("Please upload and process PDFs first.")

    with st.sidebar:
        st.subheader("Your documents")
        
        if st.button("🧹 Clear Chat"):
            st.session_state.chat_history = []

            if st.session_state.conversation:
                st.session_state.conversation.memory.clear()

            st.rerun()

        pdf_docs = st.file_uploader("Upload your PDF documents here and click on Process", accept_multiple_files=True)
        if st.button("Process"):
            with st.spinner("Processing"):
                # Get PDF text 
                raw_text = get_pdf_text(pdf_docs)
                st.write(raw_text)

                # Get the text chunks
                text_chunks = get_text_chunks(raw_text)

                # Create vector store with our text embeddings
                vectorstore = get_vectorstores(text_chunks)

                # create conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore)
    
  
if __name__ == '__main__':
    main()
