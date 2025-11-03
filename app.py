import streamlit as st
from github import Github
import openai
import json
import os

CONFIG_ARQUIVO = "agente_config.json"

# Função para carregar configurações salvas
def carregar_config():
    if os.path.exists(CONFIG_ARQUIVO):
        with open(CONFIG_ARQUIVO, "r") as f:
            return json.load(f)
    return {}

# Função para salvar configurações
def salvar_config(config):
    with open(CONFIG_ARQUIVO, "w") as f:
        json.dump(config, f)

# Carregando configurações salvas
config = carregar_config()

# ----- SIDEBAR: Configuração do agente -----
st.sidebar.header("Configurações do GitHub e IA")

github_user = st.sidebar.text_input("Usuário do GitHub", value=config.get("github_user", ""))
github_repo = st.sidebar.text_input("Repositório", value=config.get("github_repo", ""))
github_token = st.sidebar.text_input("Token do GitHub", type="password", value=config.get("github_token", ""))
github_branch = st.sidebar.text_input("Branch", value=config.get("github_branch", "main"))
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password", value=config.get("openai_api_key", ""))

if st.sidebar.button("Salvar configurações", key="btn_salvar_config"):
    salvar_config({
        "github_user": github_user,
        "github_repo": github_repo,
        "github_token": github_token,
        "github_branch": github_branch,
        "openai_api_key": openai_api_key
    })
    st.sidebar.success("Configurações salvas com sucesso!")

# ----- Conectando ao GitHub -----
if all([github_user, github_repo, github_token, github_branch]):
    try:
        g = Github(github_token)
        repo = g.get_user(github_user).get_repo(github_repo)
        st.session_state['repo'] = repo
        st.session_state['github_branch'] = github_branch
        st.success(f"Conectado ao GitHub: {github_user}/{github_repo} [{github_branch}]")
    except Exception as erro:
        st.error(f"Erro ao conectar ao GitHub: {erro}")

if openai_api_key:
    openai.api_key = openai_api_key

st.set_page_config(page_title="Super Agente IA", page_icon="🤖", layout="wide")
st.title("🤖 Super Agente IA - Upload, Botões, GitHub e IA Automático")

# 1. Chat com IA (GPT-3.5) - Histórico Registrado
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.expander("💬 Chat com IA (GPT-3.5)"):
    user_prompt = st.text_area("Pergunte algo para a IA:")
    if st.button("Perguntar", key="btn_perguntar_ia"):
        if user_prompt.strip() != "" and openai_api_key:
            with st.spinner("A IA está escrevendo..."):
                try:
                    resposta = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": user_prompt}]
                    ).choices[0].message.content
                    st.success(resposta)
                    st.session_state.chat_history.append((user_prompt, resposta))
                except Exception as error:
                    st.error(f"Erro da OpenAI: {error}")
    if st.session_state.chat_history:
        st.markdown("**Histórico do Chat**:")
        for pergunta, resposta in st.session_state.chat_history:
            st.markdown(f"**Você:** {pergunta}")
            st.markdown(f"**IA:** {resposta}")

# 2. Upload de Arquivo Único para GitHub
with st.expander("📤 Upload de Arquivo para GitHub"):
    if st.session_state.get('repo'):
        uploaded_file = st.file_uploader("Escolha um arquivo para enviar ao GitHub", key="upfile_unico")
        caminho = st.text_input("Destino no repositório (ex: pasta/arquivo.txt)", value="", key="dest_unico")
        if st.button("Enviar arquivo para o GitHub", key="btn_upload_unico"):
            if uploaded_file is not None:
                try:
                    file_content = uploaded_file.read()
                    caminho_final = caminho.strip() if caminho else uploaded_file.name
                    repo = st.session_state['repo']
                    branch = st.session_state['github_branch']
                    try:
                        repo.create_file(caminho_final, "Upload pela interface", file_content, branch=branch)
                        st.success("Arquivo enviado com sucesso!")
                        st.session_state.atualiza_lista = True
                    except Exception:
                        # Se já existe, tente atualizar
                        current_file = repo.get_contents(caminho_final, ref=branch)
                        repo.update_file(caminho_final, "Atualização pela interface", file_content, current_file.sha, branch=branch)
                        st.info("Arquivo atualizado com sucesso!")
                        st.session_state.atualiza_lista = True
                except Exception as e:
                    st.error(f"Erro ao enviar arquivo: {e}")
            else:
                st.warning("Selecione um arquivo.")

# 3. Upload de Múltiplos Arquivos
with st.expander("📦 Upload de múltiplos arquivos"):
    if st.session_state.get('repo'):
        arquivos = st.file_uploader(
            "Selecione um ou mais arquivos para enviar ao repositório",
            accept_multiple_files=True,
            key="multi_upfile"
        )
        pasta_destino = st.text_input("Pasta destino (ex: docs/, src/)", key="multi_folder")
        if st.button("Enviar múltiplos arquivos", key="btn_upload_multi"):
            if arquivos:
                repo = st.session_state['repo']
                branch = st.session_state['github_branch']
                sucesso, erros = 0, []
                for arq in arquivos:
                    nome_arquivo = arq.name
                    conteudo = arq.read()
                    caminho_final = f"{pasta_destino.strip().rstrip('/')}/{nome_arquivo}" if pasta_destino.strip() else nome_arquivo
                    try:
                        repo.create_file(caminho_final, "Upload múltiplo", conteudo, branch=branch)
                        sucesso += 1
                        st.session_state.atualiza_lista = True
                    except Exception:
                        try:
                            current_file = repo.get_contents(caminho_final, ref=branch)
                            repo.update_file(caminho_final, "Atualização múltipla", conteudo, current_file.sha, branch=branch)
                            sucesso += 1
                            st.session_state.atualiza_lista = True
                        except Exception as err:
                            erros.append(f"{nome_arquivo}: {err}")
                if sucesso:
                    st.success(f"{sucesso} arquivo(s) enviados/atualizados com sucesso!")
                if erros:
                    st.error("Alguns arquivos tiveram erro:")
                    for erro in erros:
                        st.write(erro)
            else:
                st.warning("Selecione pelo menos um arquivo.")

# 4. Listar, Visualizar, Deletar Arquivos (revisado)
with st.expander("📂 Arquivos no Repositório"):
    if st.session_state.get('repo'):
        repo = st.session_state['repo']
        branch = st.session_state['github_branch']
        if "atualiza_lista" not in st.session_state:
            st.session_state.atualiza_lista = True

        if st.button("Atualizar lista de arquivos", key="btn_atualiza_lista"):
            st.session_state.atualiza_lista = True

        if st.session_state.atualiza_lista:
            st.session_state.arquivos_disponiveis = [arquivo.path for arquivo in repo.get_contents("") if arquivo.type == "file"]
            st.session_state.atualiza_lista = False

        if st.session_state.get("arquivos_disponiveis"):
            selecionado = st.selectbox("Escolha o arquivo:", st.session_state.arquivos_disponiveis, key="select_viz_deletar")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Visualizar arquivo", key="btn_viz"):
                    conteudo = repo.get_contents(selecionado, ref=branch)
                    st.code(conteudo.decoded_content.decode('utf-8', errors='ignore'), language="text")
            with col2:
                if st.button("Deletar arquivo", key="btn_del"):
                    conteudo = repo.get_contents(selecionado, ref=branch)
                    repo.delete_file(conteudo.path, "Arquivo deletado pela interface", conteudo.sha, branch=branch)
                    st.success(f"Arquivo {selecionado} deletado!")
                    st.session_state.atualiza_lista = True
        else:
            st.info("Não há arquivos no repositório!")

# 5. Abrir Site Publicado (GitHub Pages)
if st.session_state.get('repo'):
    site_url = f"https://{github_user}.github.io/{github_repo}/"
    with st.expander("🌐 Abrir site publicado via GitHub Pages"):
        st.write("Seu site estará disponível neste endereço:")
        st.markdown(f"[Clique aqui para abrir o site]({site_url})")
        st.info("Se o site não abrir, verifique se o GitHub Pages foi ativado nas configurações do repositório.")

    # 6. Publicar/Atualizar arquivo HTML para GitHub Pages
    st.header("🚀 Publicar/Atualizar site no GitHub Pages")
    uploaded_html = st.file_uploader("Selecione arquivo HTML para publicar/atualizar:", type=["html"], key="html_upload")
    if st.button("Publicar/Atualizar site", key="btn_pub_site"):
        if uploaded_html is not None:
            html_content = uploaded_html.read()
            repo = st.session_state['repo']
            branch = st.session_state['github_branch']
            try:
                repo.create_file("index.html", "Publicação pelo Super Agente", html_content, branch=branch)
                st.success(f"Site publicado! Veja: {site_url}")
                st.markdown(f"[Abrir site publicado]({site_url})")
            except Exception:
                try:
                    current_file = repo.get_contents("index.html", ref=branch)
                    repo.update_file("index.html", "Atualização pelo Super Agente", html_content, current_file.sha, branch=branch)
                    st.success(f"Site atualizado! Veja: {site_url}")
                    st.markdown(f"[Abrir site publicado]({site_url})")
                except Exception as err:
                    st.error(f"Erro ao atualizar site: {err}")
        else:
            st.warning("Selecione um arquivo HTML antes.")

st.info("Configurações ficam gravadas no arquivo agente_config.json! Todos os botões usam chave única/key para máxima estabilidade. Peça por outras personalizações!")
