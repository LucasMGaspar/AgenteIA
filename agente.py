import streamlit as st
import os
import base64
from dotenv import load_dotenv
from googlesearch import search  # Certifique-se de instalar com "pip install googlesearch-python"

# LangChain/IA
from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

# ------------------------ CONFIGURAÇÕES INICIAIS ------------------------
load_dotenv()
st.set_page_config(
    page_title="Assistente Virtual NavSupply",
    layout="wide"
)

# ------------------------ CSS PERSONALIZADO ------------------------
css = """
<style>
/* Fundo geral (Navy) e texto em branco */
body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"] {
    background-color: #1F3C73 !important;
    color: #FFFFFF !important;
}

/* Título centralizado */
h1 {
    text-align: center;
}

/* Contêiner principal para centralizar o chat */
.chat-container {
    max-width: 800px;
    margin: 0 auto;
    margin-top: 30px;
}

/* Mensagens do usuário (Gold) e do assistente (também Gold, para uniformidade) */
[data-testid="stChatMessage-user"],
[data-testid="stChatMessage-assistant"] {
    background-color: #C9A15D !important;
    color: #000000 !important; /* texto em preto para contraste */
    margin-bottom: 10px;
    border-radius: 8px;
    padding: 10px;
    width: 100%; /* ocupa toda a largura do contêiner */
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
}

/* Ajusta fonte geral */
html, body, [class*="css"] {
    font-family: "Arial", sans-serif;
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ------------------------ FUNÇÃO DE BUSCA NO GOOGLE ------------------------
def google_search(query):
    """
    Realiza uma busca no Google e retorna os 3 primeiros resultados (URLs).
    """
    results = []
    try:
        for url in search(query, tld="com", num=3, stop=3, pause=2):
            results.append(url)
    except Exception as e:
        st.error(f"Erro ao buscar na web: {e}")
    return results

# ------------------------ FUNÇÕES COM CACHE ------------------------
@st.cache_data
def load_documents():
    """Carrega os documentos do CSV uma única vez."""
    loader = CSVLoader(file_path="merged_data.csv", encoding="utf-8")
    documents = list(loader.lazy_load())
    return documents

@st.cache_resource
def get_vectorstore(documents):
    """Cria e retorna o índice vetorial utilizando embeddings."""
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    return vectorstore

# Carregar documentos e construir o índice vetorial (aproveitando o cache)
documents = load_documents()
db = get_vectorstore(documents)

def retrieve_info(query):
    similar_response = db.similarity_search(query, k=3)
    return [doc.page_content for doc in similar_response]

# ------------------------ INICIALIZA O MODELO DE CHAT ------------------------
lm = ChatOpenAI(temperature=0, model="gpt-4o")

# ------------------------ TEMPLATE DA ASSISTENTE ------------------------
template = """Você é uma assistente virtual altamente especializada que trabalha para a NavSupply, uma empresa de vendas marítimas. Seu papel é apoiar os compradores de materiais da empresa, respondendo a dúvidas e fornecendo informações precisas sobre temas relacionados ao setor marítimo. Para desempenhar essa função, você deve possuir amplo conhecimento em diversas áreas, incluindo:

Navegação: Entendimento dos conceitos básicos e avançados de navegação, regulamentações marítimas, rotas e procedimentos de segurança.
Comércio Exterior: Conhecimento sobre importação, exportação, regulamentações alfandegárias e processos de logística internacional.
Navios e Transporte Marítimo: Informações detalhadas sobre diferentes tipos de navios, suas funções, especificações técnicas e operações.
Tripulação e Operações: Conhecimento sobre as funções e responsabilidades da tripulação, gestão de pessoal a bordo e procedimentos de emergência.
Componentes e Equipamentos de Navios: Familiaridade com os diversos objetos e materiais utilizados em navios, desde equipamentos de navegação até itens de manutenção.
Materiais de Salvamento: Conhecimento dos dispositivos e materiais essenciais para a segurança e salvamento no mar.
Códigos e Normas IMPA: Entendimento das diretrizes e códigos IMPA (International Marine Purchasing Association) que regulam processos e práticas de compras e manutenção no setor marítimo.
Sua comunicação deve ser clara, objetiva e precisa, de modo a fornecer respostas que auxiliem os compradores na tomada de decisões informadas sobre a aquisição de materiais e na resolução de dúvidas técnicas e operacionais.
Além disso, se a consulta estiver relacionada a algum material específico, forneça uma descrição detalhada sobre sua aplicação e para que ele é utilizado, de modo a ajudar o comprador que não conhece o material."""

# ------------------------ INTERFACE DE CHAT ------------------------
st.title("Assistente Virtual NavSupply")

st.markdown('<div class="chat-container">', unsafe_allow_html=True)

if "conversation" not in st.session_state:
    st.session_state.conversation = []

for message in st.session_state.conversation:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        st.chat_message("assistant").write(message["content"])

user_input = st.chat_input("Digite sua pergunta:")

if user_input:
    st.session_state.conversation.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    
    # Recupera informações relevantes do CSV com cache
    context_info = retrieve_info(user_input)
    # Se não encontrar informações concretas no CSV, aciona a busca no Google
    if not context_info or all(not item.strip() for item in context_info):
        web_results = google_search(user_input)
        web_context = "\n".join(web_results)
        final_context = f"Resultados da Web:\n{web_context}"
    else:
        final_context = "Contexto do CSV:\n" + "\n".join(context_info)
    
    # Monta o prompt final incorporando o contexto relevante
    full_prompt = f"{template}\n\n{final_context}\n\nPergunta: {user_input}"
    
    messages = [HumanMessage(content=full_prompt)]
    response = lm(messages)
    answer = response.content
    
    st.session_state.conversation.append({"role": "assistant", "content": answer})
    st.chat_message("assistant").write(answer)

st.markdown('</div>', unsafe_allow_html=True)
