"""TrustRAG local demo: isolated documents, cited answers and explicit abstention."""

import hashlib
import json
import os
from pathlib import Path
import uuid

from dotenv import load_dotenv
import streamlit as st

load_dotenv()
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from langchain_qdrant import Qdrant  # noqa: E402
from ragbase.config import load_config  # noqa: E402
from ragbase.generation.generator import AnswerGenerator  # noqa: E402
from ragbase.ingestion.indexer import build_index  # noqa: E402
from ragbase.model import create_embeddings  # noqa: E402
from ragbase.retrieval.hybrid import RetrievalPipeline  # noqa: E402

ROOT = Path(__file__).resolve().parent
MODES = {"Dense + 重排": "dense_reranker", "Dense": "baseline", "BM25": "bm25", "混合检索": "hybrid", "混合检索 + 重排": "hybrid_reranker"}

st.set_page_config(page_title="TrustRAG", page_icon="📚", layout="wide")
st.title("TrustRAG")
st.caption("从资料中回答，给出可核对的来源；证据不足时明确拒答。")
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
    st.session_state.messages = []

with st.sidebar:
    st.header("知识库")
    knowledge_mode = st.radio("资料来源", ["企业演示知识库", "上传 PDF"])
    selected_mode = st.selectbox("检索方式", list(MODES))
    uploaded = st.file_uploader("选择 PDF 文档", type=["pdf"], accept_multiple_files=True) if knowledge_mode == "上传 PDF" else []
    if knowledge_mode == "企业演示知识库":
        st.caption("10 份虚构企业政策，120 页。证据门限默认关闭。")
    else:
        st.caption("上传文档只保存在当前本地会话目录。使用提示词拒答与引用核验。")
    if st.button("清空聊天记录"):
        st.session_state.messages = []
        st.rerun()

config = load_config(ROOT / "configs/demo" / (MODES[selected_mode] + ".yaml"))
if knowledge_mode == "上传 PDF" and not uploaded:
    st.info("先上传 PDF 文档，再输入问题。")
    st.stop()

if knowledge_mode == "企业演示知识库":
    paths = sorted((ROOT / "data/documents").glob("*.pdf"))
    fingerprint = "demo:" + config.chunking.strategy
else:
    fingerprint = hashlib.sha256(b"".join(file.name.encode() + file.getvalue() for file in uploaded)).hexdigest()
    storage = ROOT / ".runtime" / "app_sessions" / st.session_state.session_id / "documents" / fingerprint
    storage.mkdir(parents=True, exist_ok=True)
    paths = []
    names = set()
    for file in uploaded:
        filename = file.name.replace("\\", "/").rsplit("/", 1)[-1]
        if filename in names or not filename.lower().endswith(".pdf"):
            st.error("请使用不同文件名的 PDF 文档。")
            st.stop()
        names.add(filename)
        path = storage / filename
        if not path.exists():
            path.write_bytes(file.getvalue())
        paths.append(path)

if st.session_state.get("corpus_fingerprint") != fingerprint:
    previous = st.session_state.get("index")
    if previous:
        previous.close()
    st.session_state.messages = []
    try:
        with st.spinner("正在建立资料索引…"):
            index = build_index(paths, config, ROOT / ".runtime/app_sessions" / st.session_state.session_id / "indexes")
            # Each session owns one client. Reopen it for Streamlit's script-thread
            # lifecycle; queries are serialized per session, and indexing is complete.
            index.close()
            index.vector_store = Qdrant.from_existing_collection(embedding=create_embeddings(config), collection_name="documents",
                                                                path=index.path / "qdrant", force_disable_check_same_thread=True)
            st.session_state.index = index
            st.session_state.corpus_fingerprint = fingerprint
    except Exception as error:
        st.error(f"索引建立失败：{error}")
        st.stop()

index = st.session_state.index
calibration = json.loads((ROOT / config.answerability.calibration_file).read_text(encoding="utf-8"))
calibrated = calibration["index_id"] == index.manifest["index_id"]
if calibrated:
    st.caption(f"当前知识库：{len(paths)} 份文档 · {index.manifest['chunk_count']} 个片段 · 提示词拒答与引用核验")
else:
    st.info("当前资料尚未完成独立评测，使用提示词拒答与引用核验；证据门限默认关闭。")


def show_answer(payload):
    st.markdown(payload["answer"])
    gate = payload["gate"]
    columns = st.columns(3)
    columns[0].metric("回答状态", "拒答" if payload["abstained"] else "已回答")
    columns[1].metric("证据评分", f"{gate['confidence']:.4f}")
    columns[2].metric("证据门限", "关闭" if gate["reason"] == "gate_disabled" else f"{gate['threshold']:.4f}")
    st.caption(f"检索方式：{payload['retrieval_mode']} · 分数特征：{gate['feature']}。评分衡量检索证据，不是答案正确概率；门限暂为实验功能。")
    if payload["sources"]:
        st.markdown("**Sources / 来源**")
        cited = set(payload["citation_validation"]["cited_ids"])
        for source in payload["sources"]:
            marker = " · 已引用" if source["source_id"] in cited and not payload["abstained"] else ""
            with st.expander(f"[{source['source_id']}] {source['filename']} — Page {source['page']}{marker}"):
                st.write(source["text"])
    with st.expander("Retrieved Evidence / 检索证据"):
        for evidence in payload["evidence"][:5]:
            st.write(f"{evidence['metadata']['filename']} · Page {evidence['metadata']['page']} · score={evidence['score']:.4f}")
            st.write(evidence["text"][:1024])


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            show_answer(message["payload"])
        else:
            st.markdown(message["content"])

if question := st.chat_input("输入一个自包含的问题，例如：How much paid sick leave do employees receive?"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            with st.spinner("正在检索资料并核对来源…"):
                batch = RetrievalPipeline(config, index).retrieve(question)
                answer = AnswerGenerator(config).generate(question, batch.results)
                payload = {**answer.to_dict(), "retrieval_mode": selected_mode, "evidence": [result.to_dict() for result in batch.results]}
            show_answer(payload)
            st.session_state.messages.append({"role": "assistant", "payload": payload})
        except Exception as error:
            st.error(f"问答失败：{error}")
