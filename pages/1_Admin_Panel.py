import streamlit as st
import pandas as pd
import os
import re
from src.utils.db import add_user, get_all_users, delete_user, update_user_password_admin, get_user
from src.utils.auth import hash_password, format_codigo_loterico
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
                            raw_codigo = str(row['codigo_loterico']).strip()
                            senha = str(row['senha_temporaria']).strip()
                            
                            nome = ''
                            if 'nome_loterica' in df.columns and not pd.isna(row['nome_loterica']):
                                nome = str(row['nome_loterica']).strip()
                                
                            if raw_codigo and senha:
                                codigo = format_codigo_loterico(raw_codigo)
                                if len(re.sub(r'\D', '', raw_codigo)) == 9:
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
        raw_new_user = st.text_input("Novo Código Lotérico:")
        new_nome = st.text_input("Nome da Lotérica (Opcional):")
        new_pass = st.text_input("Senha Temporária:")
        
        if st.button("Criar Usuário"):
            if raw_new_user and new_pass:
                formatted_new_user = format_codigo_loterico(raw_new_user)
                if len(re.sub(r'\D', '', raw_new_user)) != 9:
                    st.error("O código lotérico deve conter exatamente 9 dígitos numéricos.")
                else:
                    success = add_user(formatted_new_user, hash_password(new_pass), nome_loterica=new_nome)
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
                    raw_user_to_del = st.text_input("Digite o Código do Usuário para Excluir (somente números)", key="del_input")
                    if st.button("Excluir"):
                        if len(re.sub(r'\D', '', raw_user_to_del)) != 9:
                            st.error("O código deve ter 9 dígitos numéricos.")
                        else:
                            formatted_del = format_codigo_loterico(raw_user_to_del)
                            if formatted_del == "00.000000-0":
                                st.error("Não é possível excluir o administrador mestre.")
                            else:
                                user_exists = get_user(formatted_del)
                                if user_exists:
                                    delete_user(formatted_del)
                                    st.success(f"Usuário {formatted_del} excluído.")
                                    st.rerun()
                                else:
                                    st.error("Usuário não encontrado.")
            
            with col_reset:
                with st.expander("Redefinir Senha"):
                    raw_user_to_reset = st.text_input("Digite o Código do Usuário para Redefinir Senha (somente números)", key="reset_input")
                    new_temp_pass = st.text_input("Nova Senha Temporária")
                    if st.button("Redefinir"):
                        if not new_temp_pass:
                            st.warning("Preencha a nova senha.")
                        elif len(re.sub(r'\D', '', raw_user_to_reset)) != 9:
                            st.error("O código deve ter 9 dígitos numéricos.")
                        else:
                            formatted_reset = format_codigo_loterico(raw_user_to_reset)
                            user_exists = get_user(formatted_reset)
                            if user_exists:
                                update_user_password_admin(formatted_reset, hash_password(new_temp_pass))
                                st.success(f"Senha do usuário {formatted_reset} redefinida.")
                                st.rerun()
                            else:
                                st.error("Usuário não encontrado.")
        else:
            st.info("Nenhum usuário encontrado para a busca.")
    else:
        st.info("Nenhum usuário cadastrado.")

with tab2:
    st.header("Sincronização com Google Drive")
    st.write("Esta seção permite que o sistema baixe automaticamente todos os PDFs da sua pasta do Google Drive e os processe na Inteligência Artificial (Gemini).")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        api_key = None
        
    if not api_key:
        st.error("Configure a GOOGLE_API_KEY nas secrets do Streamlit Cloud.")
        
    drive_folder_id = st.text_input("ID da Pasta do Google Drive (Ex: 1A2B3C4D5E...)", value="1RXbdy_QwW9yG5CA_uECcSH6M_vGYd6gd")
    
    if st.button("🔄 Sincronizar Google Drive e Atualizar IA", type="primary"):
        try:
            gcp_creds = st.secrets.get("gcp_service_account")
        except Exception:
            gcp_creds = None
            
        if not gcp_creds:
            st.error("As credenciais do Google Cloud ('gcp_service_account') não foram configuradas nas Secrets do Streamlit.")
        elif not api_key:
            st.error("A chave do Gemini ('GOOGLE_API_KEY') não foi encontrada nas Secrets.")
        elif not drive_folder_id:
            st.warning("Por favor, preencha o ID da pasta do Drive.")
        else:
            with st.spinner("Passo 1/2: Baixando PDFs do Google Drive (pode levar alguns minutos)..."):
                from src.utils.drive import get_drive_service, download_pdfs_from_folder, clear_directory
                from src.utils.rag import DOCS_DIR
                
                service = get_drive_service(dict(gcp_creds))
                if service:
                    clear_directory(DOCS_DIR)
                    success_dl, msg_dl = download_pdfs_from_folder(service, drive_folder_id, DOCS_DIR)
                    
                    if success_dl:
                        st.success(f"Arquivos baixados! Iniciando processamento de IA...")
                        with st.spinner("Passo 2/2: A IA está lendo os documentos (Isso pode demorar dependendo do tamanho e quantidade de PDFs)..."):
                            from src.utils.rag import process_documents
                            try:
                                success_rag, msg_rag = process_documents(api_key)
                                if success_rag:
                                    st.success(f"Tudo pronto! {msg_rag}")
                                else:
                                    st.error(f"Erro no processamento da IA: {msg_rag}")
                            except Exception as ai_err:
                                st.error(f"Falha na API do Google Gemini. Verifique se a sua chave (GOOGLE_API_KEY) é válida, possui créditos ou permissões ativas. Erro técnico: {ai_err}")
                    else:
                        st.error(f"Erro ao baixar do Drive: {msg_dl}")
                else:
                    st.error("Falha ao autenticar com o Google Drive (Credenciais inválidas).")

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
