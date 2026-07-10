import streamlit as st
import os
import re
from src.utils.db import init_db, get_user, update_password, add_user
from src.utils.auth import check_password, hash_password, format_codigo_loterico

st.set_page_config(page_title="Mestre Lotérico - Login", page_icon="🎫", layout="centered")

def init_app():
    init_db()
    admin_user = get_user("00.000000-0")
    if not admin_user:
        add_user("00.000000-0", hash_password("admin123"), role="admin", must_change_password=False)

if 'user' not in st.session_state:
    st.session_state.user = None

def login_page():
    st.title("Mestre Lotérico 🎫")
    st.subheader("Faça login para acessar")
    
    with st.form("login_form"):
        # Alterado para solicitar apenas números do código (TRAVADO EM 9 CARACTERES)
        raw_codigo = st.text_input("Digite seu código lotérico", placeholder="Somente números (ex: 123456789)", max_chars=9)
        senha = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        
        if submitted:
            # Verifica se digitou letras antes mesmo de formatar
            if not raw_codigo.isdigit():
                st.error("Por favor, digite APENAS números no código lotérico (sem letras, pontos ou traços).")
            else:
                codigo = format_codigo_loterico(raw_codigo)
                user = get_user(codigo)
                if user and check_password(senha, user['password_hash']):
                    st.session_state.user = user
                    st.rerun()
                else:
                    if len(raw_codigo) != 9:
                        st.error("O código lotérico deve conter exatamente 9 dígitos numéricos.")
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
