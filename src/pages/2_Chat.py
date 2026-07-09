import streamlit as st
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from src.utils.rag import get_vectorstore
from src.utils.sponsors import get_active_sponsor

st.set_page_config(page_title="Mestre Lotérico - Chat", page_icon="💬", layout="wide")

if 'user' not in st.session_state or not st.session_state.user:
    st.error("Acesso negado. Por favor, faça login.")
    st.stop()

if st.session_state.user.get('must_change_password'):
    st.warning("Você precisa alterar sua senha na página inicial antes de usar o chat.")
    st.stop()

# Layout
col_chat, col_sidebar = st.columns([3, 1])

with col_sidebar:
    st.title("Menu")
    st.page_link("app.py", label="Voltar para o Início")
    
    st.markdown("---")
    sponsor = get_active_sponsor()
    if sponsor:
        st.write("**Patrocínio:**")
        st.image(sponsor['image_path'], use_column_width=True)
        st.markdown(f"[{sponsor['name']}]({sponsor['link']})")
    else:
        st.info("Espaço para patrocinadores. Anuncie aqui!")
        
    st.markdown("---")
    st.subheader("Configurações")
    api_key = st.text_input("Chave API do Google Gemini", type="password", key="chat_api_key")

with col_chat:
    st.title("Mestre Lotérico 💬")
    st.write("Faça suas perguntas sobre as regras da CAIXA.")

    if not api_key:
        st.warning("Por favor, insira sua chave da API do Gemini no menu lateral para começar.")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    if "memory" not in st.session_state:
        st.session_state.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

    # Initialize RAG chain if not exists
    if "qa_chain" not in st.session_state or st.session_state.get('last_api_key') != api_key:
        vectorstore = get_vectorstore(api_key)
        if not vectorstore:
            st.error("Base de conhecimento não encontrada. O administrador precisa processar os documentos no Painel Admin.")
            st.stop()
            
        llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0, google_api_key=api_key)
        
        # Custom prompt to force answering ONLY from context
        prompt_template = """Você é o "Mestre Lotérico", um assistente especialista nas regras da CAIXA para unidades lotéricas.
Você deve responder às dúvidas dos usuários usando SOMENTE as informações fornecidas no contexto abaixo.
Se a resposta não estiver no contexto, diga exatamente: "Desculpe, não encontrei essa informação nos documentos oficiais da CAIXA fornecidos."
Não invente informações e não use conhecimentos externos.

Contexto:
{context}

Histórico da conversa:
{chat_history}

Pergunta do usuário: {question}
Resposta detalhada em português do Brasil:"""

        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "chat_history", "question"]
        )

        st.session_state.qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(search_kwargs={"k": 4}),
            memory=st.session_state.memory,
            combine_docs_chain_kwargs={"prompt": PROMPT}
        )
        st.session_state.last_api_key = api_key

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("Digite sua dúvida sobre regras da CAIXA aqui..."):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Consultando manuais da CAIXA..."):
                try:
                    response = st.session_state.qa_chain({"question": prompt})
                    answer = response['answer']
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"Erro ao gerar resposta: {e}")
