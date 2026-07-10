import streamlit as st
import pandas as pd
import os
from src.utils.db import add_user, get_all_users, delete_user, update_user_password_admin
from src.utils.auth import hash_password
from src.utils.sponsors import add_sponsor, get_all_sponsors, set_active_sponsor, delete_sponsor

st.set_page_config(page_title="Admin Panel", page_icon="⚙️")

if 'user' not in st.session_state or not st.session_state.user or st.session_state.user['role'] != 'admin':
    st.error("Acesso negado. Você precisa ser administrador para acessar esta página.")
    st.stop()

st.title("Painel Administrativo - Mestre Lotérico ⚙️")

tab1, tab2, tab3 = st.tabs(["Gerenciar Usuários", "Gerenciar Documentos CAIXA", "Gerenciar Patrocinadores"])

with tab1:
    st.header("Importar Usuários em Lote (CSV)")
    st.write("O arquivo CSV deve conter as colunas: `codigo_loterico`, `senha_temporaria` e (opcional) `nome_loterica`.")
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
                            
                            nome = ''
                            if 'nome_loterica' in df.columns and not pd.isna(row['nome_loterica']):
                                nome = str(row['nome_loterica']).strip()
                                
                            if codigo and senha:
                                success = add_user(codigo, hash_password(senha), role='user', must_change_password=True, nome_loterica=nome)
                                if success:
                                    success_count += 1
                        st.success(f"{success_count} usuários importados com sucesso!")
            else:
                st.error("O CSV deve conter as colunas 'codigo_loterico' e 'senha_temporaria'.")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")
            
    st.markdown("---")
    st.header("Gerenciar Acessos")
    
    # 1. ADD NEW USER
    with st.expander("Adicionar Novo Usuário Manualmente"):
        new_user = st.text_input("Novo Código Lotérico")
        new_nome = st.text_input("Nome da Lotérica (Opcional)")
        new_pass = st.text_input("Senha Temporária")
        
        if st.button("Criar Usuário"):
            if new_user and new_pass:
                success = add_user(new_user, hash_password(new_pass), nome_loterica=new_nome)
                if success:
                    st.success("Usuário criado com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro: Usuário (código) já existe.")
            else:
                st.warning("Preencha o código e a senha.")

    st.subheader("Usuários Cadastrados")
    users = get_all_users()
    if users:
        search_query = st.text_input("🔍 Buscar Usuário (por Código ou Nome da Lotérica)", placeholder="Digite para filtrar...")
        
        # Filtra usuários
        filtered_users = []
        for u in users:
            codigo = u.get('codigo_loterico', '').lower()
            nome = u.get('nome_loterica', '').lower()
            if search_query.lower() in codigo or search_query.lower() in nome:
                filtered_users.append(u)
                
        if filtered_users:
            df_users = pd.DataFrame(filtered_users)
            st.dataframe(df_users, use_container_width=True)
            
            st.write("### Ações de Usuário")
            col_del, col_reset = st.columns(2)
            with col_del:
                with st.expander("Excluir Usuário"):
                    user_to_del = st.selectbox("Selecione o Usuário para Excluir", [u['codigo_loterico'] for u in filtered_users if u['role'] != 'admin'])
                    if st.button("Excluir"):
                        delete_user(user_to_del)
                        st.success("Usuário excluído.")
                        st.rerun()
            
            with col_reset:
                with st.expander("Redefinir Senha"):
                    user_to_reset = st.selectbox("Selecione o Usuário para Redefinir Senha", [u['codigo_loterico'] for u in filtered_users if u['role'] != 'admin'])
                    new_temp_pass = st.text_input("Nova Senha Temporária")
                    if st.button("Redefinir"):
                        if new_temp_pass:
                            update_user_password_admin(user_to_reset, hash_password(new_temp_pass))
                            st.success("Senha redefinida.")
                            st.rerun()
                        else:
                            st.warning("Preencha a nova senha.")
        else:
            st.info("Nenhum usuário encontrado para a busca.")
    else:
        st.info("Nenhum usuário cadastrado.")

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
                if st.button("Excluir", key=f"del_{doc}"):
                    os.remove(os.path.join(docs_dir, doc))
                    st.rerun()
    else:
        st.info("Nenhum documento cadastrado.")
        
    st.subheader("Processamento de Inteligência Artificial")
    st.write("Aqui você pode processar os PDFs atuais e também importar documentos diretamente do Google Drive.")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        api_key = None
        
    if not api_key:
        st.error("Configure a GOOGLE_API_KEY nas secrets do Streamlit Cloud.")
        
    st.markdown("### 1. Importar PDFs do Google Drive (Opcional)")
    st.write("Para buscar os arquivos de uma pasta do Google Drive, adicione o Folder ID abaixo. As credenciais (JSON) devem estar em `st.secrets['gcp_service_account']`.")
    drive_folder_id = st.text_input("ID da Pasta do Google Drive (Ex: 1A2B3C4D5E...)")
    if st.button("Sincronizar do Google Drive"):
        try:
            gcp_creds = st.secrets.get("gcp_service_account")
        except Exception:
            gcp_creds = None
            
        if not gcp_creds:
            st.error("As credenciais 'gcp_service_account' não foram configuradas nas Secrets do Streamlit Cloud.")
        elif not drive_folder_id:
            st.warning("Por favor, preencha o ID da pasta do Drive.")
        else:
            with st.spinner("Baixando PDFs do Google Drive... Isso pode demorar."):
                from src.utils.drive import get_drive_service, download_pdfs_from_folder, clear_directory
                from src.utils.rag import DOCS_DIR
                
                service = get_drive_service(dict(gcp_creds))
                if service:
                    # Clear existing before downloading
                    clear_directory(DOCS_DIR)
                    success_dl, msg_dl = download_pdfs_from_folder(service, drive_folder_id, DOCS_DIR)
                    if success_dl:
                        st.success(msg_dl)
                        st.rerun()
                    else:
                        st.error(msg_dl)
                else:
                    st.error("Falha ao autenticar com o Google Drive.")

    st.markdown("### 2. Processamento de Inteligência Artificial")
    st.write("Após importar ou fazer upload manual dos PDFs, atualize a base de conhecimento (VectorDB).")
    
    if st.button("Atualizar Base de Conhecimento (IA)"):
        if not api_key:
            st.error("A chave da API do Gemini não foi encontrada.")
        else:
            with st.spinner("Processando e lendo documentos... Isso pode levar alguns minutos (aproximadamente 300 documentos)."):
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
                        if st.button("Ativar", key=f"act_{s['id']}"):
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
