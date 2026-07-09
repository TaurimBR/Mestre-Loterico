import streamlit as st
import os
from src.utils.db import init_db, get_user, update_password, add_user
from src.utils.auth import check_password, hash_password

st.set_page_config(page_title="Mestre Lotérico - Login", page_icon="🎫", layout="centered")

def init_app():
    init_db()
    admin_user = get_user("admin")
    if not admin_user:
        add_user("admin", hash_password("admin123"), role="admin", must_change_password=False)

if 'user' not in st.session_state:
    st.session_state.user = None

def login_page():
    st.title("Mestre Lotérico 🎫")
    st.subheader("Faça login para acessar")
    
    with st.form("login_form"):
        codigo = st.text_input("Código Lotérico (ou 'admin')", placeholder="Ex: 12.345678-9")
        senha = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        
        if submitted:
            user = get_user(codigo)
            if user and check_password(senha, user['password_hash']):
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Código lotérico ou senha incorretos.")

def change_password_page():
    st.title("Primeiro Acesso - Alteração de Senha")
    st.warning("Para sua segurança, é obrigatório alterar a senha no primeiro acesso.")
    
    with st.form("change_password_form"):
        nova_senha = st.text_input("Nova Senha", type="password")
        confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
        submitted = st.form_submit_button("Alterar Senha")
        
        if submitted:
            if not nova_senha:
                st.error("A nova senha não pode ser vazia.")
            elif nova_senha != confirmar_senha:
                st.error("As senhas não coincidem.")
            elif len(nova_senha) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                update_password(st.session_state.user['codigo_loterico'], hash_password(nova_senha))
                st.session_state.user['must_change_password'] = 0
                st.success("Senha alterada com sucesso!")
                st.rerun()

def main():
    init_app()
    
    if not st.session_state.user:
        login_page()
    elif st.session_state.user.get('must_change_password'):
        change_password_page()
    else:
        if st.session_state.user['role'] == 'admin':
            st.switch_page("pages/1_Admin_Panel.py")
        else:
            st.switch_page("pages/2_Chat.py")

if __name__ == "__main__":
    main()
