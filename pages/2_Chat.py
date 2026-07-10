import streamlit as st
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from src.utils.rag import get_vectorstore
from src.utils.sponsors import get_active_sponsor
from src.utils.db import get_conversations, create_conversation, get_messages, add_message

st.set_page_config(page_title="Mestre Lotérico - Chat", page_icon="💬", layout="wide")

if 'user' not in st.session_state or not st.session_state.user:
    st.error("Acesso negado. Por favor, faça login.")
    st.stop()

if st.session_state.user.get('must_change_password'):
    st.warning("Você precisa alterar sua senha na página inicial antes de usar o chat.")
    st.stop()

user_info = st.session_state.user
codigo = user_info['codigo_loterico']

# Configuração de estado inicial
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

def load_conversation(conv_id):
    st.session_state.current_conversation_id = conv_id
    msgs = get_messages(conv_id)
    
    st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in msgs]
    
    # Reconstruir memória
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    # Alimentar a memória com o histórico carregado do banco de dados
    for i in range(0, len(msgs)-1, 2):
        if msgs[i]["role"] == "user" and msgs[i+1]["role"] == "assistant":
            st.session_state.memory.chat_memory.add_user_message(msgs[i]["content"])
            st.session_state.memory.chat_memory.add_ai_message(msgs[i+1]["content"])
            
def start_new_conversation():
    st.session_state.current_conversation_id = None
    st.session_state.messages = []
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

# ====== CONFIGURAÇÃO DA BARRA LATERAL ======
with st.sidebar:
    # Mostra o nome da lotérica se existir, senão o código
    display_name = user_info.get('nome_loterica')
    if not display_name or display_name.strip() == '':
        display_name = codigo
        
    st.markdown(f"## **BEM-VINDO(A)!**")
    st.write(f"Usuário: {display_name}")
    
    if st.button("➕ Novo Chat Mestre", use_container_width=True):
        start_new_conversation()
        st.rerun()
        
    if st.button("Sair", use_container_width=True):
        st.session_state.user = None
        st.switch_page("app.py")

    # Mostrar o botão Admin apenas se o usuário for admin
    if user_info['role'] == 'admin':
        st.markdown("---")
        st.page_link("pages/1_Admin_Panel.py", label="⚙️ Painel Admin")

    st.markdown("---")
    st.write("**Histórico de Conversas**")
    
    conversations = get_conversations(codigo)
    if not conversations:
        st.caption("Nenhuma conversa salva.")
    else:
        for conv in conversations:
            # Destaque se for a conversa atual
            label = f"💬 {conv['title']}"
            if conv['id'] == st.session_state.current_conversation_id:
                label = f"🟢 {conv['title']}"
                
            if st.button(label, key=f"conv_{conv['id']}", use_container_width=True):
                load_conversation(conv['id'])
                st.rerun()
        
    st.markdown("---")
    sponsor = get_active_sponsor()
    if sponsor:
        st.write("**Patrocínio:**")
        st.image(sponsor['image_path'], use_column_width=True)
        st.markdown(f"[{sponsor['name']}]({sponsor['link']})")

# ====== ÁREA PRINCIPAL DO CHAT ======
st.title("Pergunte ao Mestre Lotérico")

# ====== CONFIGURAÇÃO DA CHAVE API ======
try:
    # Tenta puxar a chave de forma segura do gerenciador de segredos
    api_key = st.secrets["GOOGLE_API_KEY"]
except (KeyError, FileNotFoundError):
    api_key = None

if not api_key:
    st.error("Chave de API não encontrada! Configure o arquivo secrets.toml (local) ou as Secrets (produção).")
    st.stop()
# =======================================

if "qa_chain" not in st.session_state or st.session_state.get('last_api_key') != api_key:
    vectorstore = get_vectorstore(api_key)
    if not vectorstore:
        st.error("Base de conhecimento não encontrada. O administrador precisa processar os documentos no Painel Admin.")
        st.stop()
        
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, google_api_key=api_key)
    
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
    
    # Se for uma nova conversa, cria no banco primeiro
    if st.session_state.current_conversation_id is None:
        # Pega os primeiros 30 caracteres do prompt para o título
        title = prompt[:30] + "..." if len(prompt) > 30 else prompt
        conv_id = create_conversation(codigo, title)
        st.session_state.current_conversation_id = conv_id
    else:
        conv_id = st.session_state.current_conversation_id

    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    add_message(conv_id, "user", prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando manuais da CAIXA..."):
            try:
                response = st.session_state.qa_chain({"question": prompt})
                answer = response['answer']
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                add_message(conv_id, "assistant", answer)
                st.rerun() # Reinicia rapidamente para o Histórico da lateral atualizar
            except Exception as e:
                st.error(f"Erro ao gerar resposta: {e}")
