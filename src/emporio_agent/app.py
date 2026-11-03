"""Web chat (Streamlit). Thin layer over chat.ask(): same agent, same persistence as the CLI.

    uv run streamlit run src/emporio_agent/app.py
"""

import json
import logging
import uuid

import streamlit as st

from emporio_agent.chat import ask, persistent_agent
from emporio_agent.config import ASSISTANT_NAME, store_now, store_status

EXAMPLES = [
    "Quais violões vocês têm até R$ 1000?",
    "Quanto custa o Takamine GD20? Dá pra parcelar?",
    "Qual o endereço e o horário da loja?",
    "Me arrependi da compra, posso devolver? Pedido 7, e-mail leticia.rocha@jmail.com",
    "Vocês vendem amplificador?",
    "Tem promoção de Black Friday?",
]

st.set_page_config(page_title="Empório da Música", page_icon="🎸")
logging.basicConfig(level=logging.WARNING)


@st.cache_resource
def get_agent():
    return persistent_agent()


def new_conversation() -> None:
    st.session_state.thread_id = f"web-{uuid.uuid4().hex[:8]}"
    st.session_state.history = []


if "thread_id" not in st.session_state:
    new_conversation()

with st.sidebar:
    st.subheader("🎸 Empório da Música")
    st.caption(store_status(store_now()))
    st.button("Nova conversa", on_click=new_conversation, use_container_width=True)
    st.caption(f"Conversa: `{st.session_state.thread_id}`")
    st.divider()
    st.caption("Experimente:")
    for example in EXAMPLES:
        if st.button(example, use_container_width=True):
            st.session_state.pending = example

st.title(f"Fale com a {ASSISTANT_NAME}")
st.caption("Assistente virtual da Empório da Música — protótipo")


def render_details(tools: list[dict], model: str | None) -> None:
    if not tools and not model:
        return
    with st.expander(f"🔧 {len(tools)} consulta(s)" if tools else "detalhes", expanded=False):
        for t in tools:
            st.code(f"{t['name']}({json.dumps(t['args'], ensure_ascii=False)})" + (" [erro]" if t["failed"] else ""))
        if model:
            st.caption(f"modelo: {model}")


for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_details(msg["tools"], msg["model"])

prompt = st.chat_input("Escreva sua mensagem...") or st.session_state.pop("pending", None)
if prompt:
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Consultando..."):
            try:
                turn = ask(get_agent(), st.session_state.thread_id, prompt)
                answer, model = turn.answer, turn.model
                tools = [{"name": c.name, "args": c.args, "failed": c.failed} for c in turn.tool_calls]
            except Exception as exc:  # noqa: BLE001 — every model in the chain failed
                logging.getLogger("emporio_agent").error("turn failed: %s: %s", type(exc).__name__, exc)
                answer, model, tools = "Tive um problema técnico agora. Pode tentar de novo em instantes?", None, []
        st.markdown(answer)
        render_details(tools, model)
    st.session_state.history.append({"role": "assistant", "content": answer, "tools": tools, "model": model})
