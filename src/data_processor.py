import os
import re
import json
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL_NAME, DOWNLOAD_DIR

logger = logging.getLogger(__name__)

# 确保下载目录存在
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def clean_text(text):
    """清理文本内容，去除无用字符"""
    if not text:
        return ""
    
    # 替换多个空格为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 替换多个换行为单个换行
    text = re.sub(r'\n+', '\n', text)
    
    # 删除URL（可选，取决于是否需要保留URL信息）
    # text = re.sub(r'https?://\S+', '', text)
    
    # 删除表情符号和特殊Unicode字符
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    
    return text.strip()

def split_text(text, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    """将文本分割成块"""
    if not text:
        return []
        
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    return text_splitter.split_text(text)

def get_embeddings_model():
    """获取嵌入模型"""
    return OllamaEmbeddings(model=EMBEDDING_MODEL_NAME)

def process_developer_data(username, data):
    """处理开发者数据，分割并创建嵌入"""
    if not data:
        logger.error(f"没有数据可处理: {username}")
        return None
    
    # 合并所有文本数据
    all_texts = []
    
    # 处理个人资料
    if data.get("profile"):
        profile_text = f"GitHub用户名: {data['profile'].get('username', '')}\n"
        profile_text += f"姓名: {data['profile'].get('name', '')}\n"
        profile_text += f"简介: {data['profile'].get('bio', '')}\n"
        profile_text += f"公司: {data['profile'].get('company', '')}\n"
        profile_text += f"位置: {data['profile'].get('location', '')}\n"
        profile_text += f"Email: {data['profile'].get('email', '')}\n"
        profile_text += f"Twitter: {data['profile'].get('twitter_username', '')}\n"
        profile_text += f"博客: {data['profile'].get('blog', '')}\n"
        
        all_texts.append(("个人资料", clean_text(profile_text)))
    
    # 处理README
    if data.get("readme"):
        all_texts.append(("个人README", clean_text(data["readme"])))
    
    # 处理博客内容
    if data.get("blog_content"):
        all_texts.append(("博客内容", clean_text(data["blog_content"])))
    
    # 处理语言统计
    if data.get("languages"):
        language_text = "编程语言使用占比:\n"
        for lang, percentage in data["languages"].items():
            language_text += f"{lang}: {percentage}%\n"
        all_texts.append(("编程语言", clean_text(language_text)))
    
    # 分割所有文本
    documents = []
    metadatas = []
    
    for source, text in all_texts:
        chunks = split_text(text)
        documents.extend(chunks)
        metadatas.extend([{"source": source, "username": username} for _ in chunks])
    
    if not documents:
        logger.warning(f"没有可用文档: {username}")
        return None
    
    # 获取嵌入模型
    embeddings = get_embeddings_model()
    
    # 创建向量存储
    vector_store = FAISS.from_texts(
        documents, 
        embeddings, 
        metadatas=metadatas
    )
    
    # 保存向量存储
    vector_store_path = os.path.join(DOWNLOAD_DIR, f"{username}_vector_store")
    vector_store.save_local(vector_store_path)
    
    # 保存原始文本数据（用于调试）
    with open(os.path.join(DOWNLOAD_DIR, f"{username}_raw_data.json"), "w", encoding="utf-8") as f:
        json.dump({
            "profile": data.get("profile", {}),
            "languages": data.get("languages", {}),
            # 不保存大型文本数据以节省空间
            "has_readme": bool(data.get("readme")),
            "has_blog_content": bool(data.get("blog_content"))
        }, f, ensure_ascii=False, indent=2)
    
    return {
        "vector_store_path": vector_store_path,
        "document_count": len(documents),
        "sources": [source for source, _ in all_texts]
    } 