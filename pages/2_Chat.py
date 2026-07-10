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

user_info = st.session_state.user

# ====== CONFIGURAÇÃO DA BARRA LATERAL ======
with st.sidebar:
    st.write("**Bem-vindo(a)!**")
    st.write(f"Usuário: {user_info['codigo_loterico']}")
    
    if st.button("Novo Chat Mestre", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    if st.button("Sair", use_container_width=True):
        st.session_state.user = None
        st.switch_page("app.py")

    # Mostrar o botão Admin apenas se o usuário for admin
    if user_info['role'] == 'admin':
        st.markdown("---")
        st.page_link("pages/1_Admin_Panel.py", label="⚙️ Painel Admin")

    st.markdown("---")
    st.write("**Histórico:**")
    
    # Exibe as últimas perguntas feitas na sessão atual
    if "messages" in st.session_state and len(st.session_state.messages) > 0:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                # Pega os primeiros 35 caracteres da pergunta
                texto = msg["content"][:35] + "..." if len(msg["content"]) > 35 else msg["content"]
                st.caption(f"🗣️ {texto}")
    else:
        st.caption("Nenhuma conversa ainda.")
        
    st.markdown("---")
    sponsor = get_active_sponsor()
    if sponsor:
        st.write("**Patrocínio:**")
        st.image(sponsor['image_path'], use_column_width=True)
        st.markdown(f"[{sponsor['name']}]({sponsor['link']})")

# ====== ÁREA PRINCIPAL DO CHAT ======
st.title("Pergunte ao Mestre Lotérico")

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    api_key = None

if not api_key:
    st.warning("O administrador precisa configurar a chave GOOGLE_API_KEY nas Secrets do Streamlit para o chat funcionar.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

if "qa_chain" not in st.session_state or st.session_state.get('last_api_key') != api_key:
    vectorstore = get_vectorstore(api_key)
    if not vectorstore:
        st.error("Base de conhecimento não encontrada. O administrador precisa processar os documentos no Painel Admin.")
        st.stop()
        
    llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0, google_api_key=api_key)
    
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

# Mostrar mensagens anteriores no chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Caixa para o usuário digitar
if prompt := st.chat_input("Digite sua dúvida..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Consultando manuais da CAIXA..."):
            try:
                response = st.session_state.qa_chain({"question": prompt})
                answer = response['answer']
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.rerun() # Reinicia rapidamente para o Histórico da lateral atualizar
            except Exception as e:
                st.error(f"Erro ao gerar resposta: {e}")
