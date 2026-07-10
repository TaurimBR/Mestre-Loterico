import streamlit as st
import pandas as pd
import os
from src.utils.db import add_user, get_all_users, delete_user, update_user_password_admin
from src.utils.auth import hash_password
from src.utils.sponsors import add_sponsor, get_all_sponsors, set_active_sponsor, delete_sponsor

st.set_page_config(page_title="Admin Panel", page_icon="⚙️", layout="wide")

if 'user' not in st.session_state or not st.session_state.user or st.session_state.user['role'] != 'admin':
    st.error("Acesso negado. Você precisa ser administrador para acessar esta página.")
    st.stop()

# ====== BARRA LATERAL DO ADMIN ======
with st.sidebar:
    st.write("**Modo Administrador**")
    st.page_link("pages/2_Chat.py", label="💬 Ir para o Chat")
    st.markdown("---")
    if st.button("Sair da Conta"):
        st.session_state.user = None
        st.switch_page("app.py")

st.title("Painel Administrativo - Mestre Lotérico ⚙️")

tab1, tab2, tab3 = st.tabs(["Gerenciar Usuários", "Gerenciar Documentos CAIXA", "Gerenciar Patrocinadores"])

with tab1:
    col_add1, col_add2 = st.columns(2)
    
    with col_add1:
        st.subheader("Adicionar Usuário Manualmente")
        with st.form("add_user_form", clear_on_submit=True):
            novo_codigo = st.text_input("Código Lotérico (Usuário)")
            nova_senha = st.text_input("Senha Temporária")
            submitted_add = st.form_submit_button("Cadastrar Usuário")
            
            if submitted_add:
                if novo_codigo and nova_senha:
                    if add_user(novo_codigo.strip(), hash_password(nova_senha.strip()), role='user', must_change_password=True):
                        st.success(f"Usuário {novo_codigo} criado com sucesso!")
                    else:
                        st.error("Erro: Esse Código Lotérico já existe.")
                else:
                    st.error("Preencha todos os campos.")

    with col_add2:
        st.subheader("Importar em Lote (CSV)")
        st.write("Colunas obrigatórias no CSV: `codigo_loterico` e `senha_temporaria`")
        uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                if 'codigo_loterico' in df.columns and 'senha_temporaria' in df.columns:
                    if st.button("Importar Usuários"):
                        with st.spinner("Importando..."):
                            success_count = 0
                            for index, row in df.iterrows():
                                codigo = str(row['codigo_loterico']).strip()
                                senha = str(row['senha_temporaria']).strip()
                                if codigo and senha:
                                    success = add_user(codigo, hash_password(senha), role='user', must_change_password=True)
                                    if success:
                                        success_count += 1
                            st.success(f"{success_count} usuários importados com sucesso!")
                else:
                    st.error("O CSV deve conter as colunas 'codigo_loterico' e 'senha_temporaria'.")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
                
    st.markdown("---")
    st.subheader("Usuários Cadastrados")
    
    users = get_all_users()
    
    # Criar uma tabela interativa para gerenciar
    for u in users:
        # Pular o usuário admin para evitar que você se delete por engano
        if u['role'] == 'admin':
            continue
            
        with st.container():
            col_u1, col_u2, col_u3, col_u4 = st.columns([2, 1, 1, 1])
            with col_u1:
                st.write(f"**{u['codigo_loterico']}**")
                if u['must_change_password']:
                    st.caption("Pendente: Trocar senha")
                else:
                    st.caption("Ativo")
            
            with col_u2:
                # Resetar/Editar Senha
                with st.popover("Resetar Senha"):
                    st.write(f"Nova senha para {u['codigo_loterico']}:")
                    new_pass = st.text_input("Senha", key=f"pass_{u['codigo_loterico']}")
                    if st.button("Confirmar Reset", key=f"btn_reset_{u['codigo_loterico']}"):
                        if new_pass:
                            update_user_password_admin(u['codigo_loterico'], hash_password(new_pass))
                            st.success("Senha resetada!")
                            st.rerun()
                        else:
                            st.error("Digite uma senha.")
            
            with col_u3:
                # Deletar usuário
                with st.popover("Excluir"):
                    st.warning("Tem certeza?")
                    if st.button("Sim, Excluir", key=f"btn_del_{u['codigo_loterico']}"):
                        delete_user(u['codigo_loterico'])
                        st.success("Deletado!")
                        st.rerun()
            
            st.divider()

with tab2:
    st.header("Upload de Documentos da CAIXA (PDF)")
    pdf_files = st.file_uploader("Faça upload dos PDFs com as regras da CAIXA", type="pdf", accept_multiple_files=True)
    
    docs_dir = "src/data/docs"
    os.makedirs(docs_dir, exist_ok=True)
    existing_docs = [f for f in os.listdir(docs_dir) if f.endswith('.pdf')]
    
    if pdf_files:
        if st.button("Salvar Novos Documentos"):
            for pdf in pdf_files:
                with open(os.path.join(docs_dir, pdf.name), "wb") as f:
                    f.write(pdf.getbuffer())
            st.success("Documentos salvos com sucesso!")
            st.rerun()

    st.subheader("Documentos Atuais")
    if existing_docs:
        for doc in existing_docs:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(doc)
            with col2:
                if st.button("Excluir", key=f"del_doc_{doc}"):
                    os.remove(os.path.join(docs_dir, doc))
                    st.rerun()
    else:
        st.info("Nenhum documento cadastrado.")
        
    st.subheader("Processamento de Inteligência Artificial")
    st.write("Após alterar os documentos, você precisa atualizar a base de conhecimento para que o chat utilize as novas informações.")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        api_key = None
        
    if not api_key:
        st.error("Configure a GOOGLE_API_KEY nas secrets do Streamlit Cloud.")
        
    if st.button("Atualizar Base de Conhecimento (IA)"):
        if not api_key:
            st.error("A chave da API não foi encontrada nas secrets.")
        else:
            with st.spinner("Processando documentos... Isso pode levar alguns minutos."):
                from src.utils.rag import process_documents
                success, msg = process_documents(api_key)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

with tab3:
    st.header("Gerenciar Patrocinadores")
    
    with st.expander("Adicionar Novo Patrocinador"):
        sponsor_name = st.text_input("Nome do Patrocinador")
        sponsor_link = st.text_input("Link do Patrocinador (URL)")
        sponsor_img = st.file_uploader("Imagem do Patrocinador", type=['png', 'jpg', 'jpeg'])
        set_active = st.checkbox("Definir como Patrocinador Ativo", value=True)
        
        if st.button("Salvar Patrocinador"):
            if sponsor_name and sponsor_link and sponsor_img:
                assets_dir = "src/assets"
                os.makedirs(assets_dir, exist_ok=True)
                img_path = os.path.join(assets_dir, sponsor_img.name)
                with open(img_path, "wb") as f:
                    f.write(sponsor_img.getbuffer())
                
                add_sponsor(sponsor_name, img_path, sponsor_link, set_active)
                st.success("Patrocinador adicionado com sucesso!")
                st.rerun()
            else:
                st.error("Preencha todos os campos (Nome, Link e Imagem).")
                
    st.subheader("Patrocinadores Cadastrados")
    sponsors = get_all_sponsors()
    if sponsors:
        for s in sponsors:
            with st.container():
                st.write("---")
                col1, col2, col3 = st.columns([2, 3, 2])
                with col1:
                    st.image(s['image_path'], width=100)
                with col2:
                    st.write(f"**{s['name']}**")
                    st.write(s['link'])
                    if s['active']:
                        st.success("ATIVO")
                    else:
                        st.warning("INATIVO")
                with col3:
                    if not s['active']:
                        if st.button("Ativar", key=f"act_spons_{s['id']}"):
                            set_active_sponsor(s['id'])
                            st.rerun()
                    if st.button("Excluir", key=f"del_spons_{s['id']}"):
                        delete_sponsor(s['id'])
                        try:
                            os.remove(s['image_path'])
                        except:
                            pass
                        st.rerun()
    else:
        st.info("Nenhum patrocinador cadastrado.")
