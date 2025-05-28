import os
import logging
import datetime
import re
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from config import EMBEDDING_MODEL_NAME, MODEL_NAME, PROMPT, DOWNLOAD_DIR, SKILL_ANALYSIS_PROMPT, TOP_K_RESULTS

logger = logging.getLogger(__name__)

def load_vector_store(username):
    """加载用户的向量存储"""
    vector_store_path = os.path.join(DOWNLOAD_DIR, f"{username}_vector_store")
    
    if not os.path.exists(vector_store_path):
        logger.error(f"向量存储不存在: {vector_store_path}")
        return None
    
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME)
    vector_store = FAISS.load_local(vector_store_path, embeddings, allow_dangerous_deserialization=True)
    
    return vector_store

def retrieve_relevant_information(username, query, top_k=TOP_K_RESULTS):
    """检索与查询相关的信息"""
    vector_store = load_vector_store(username)
    
    if not vector_store:
        logger.error(f"无法加载向量存储: {username}")
        return []
    
    try:
        # 执行相似性搜索
        search_results = vector_store.similarity_search_with_score(query, k=top_k)
        
        # 提取结果
        results = []
        for doc, score in search_results:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)  # 转换为Python原生类型，以便JSON序列化
            })
        
        return results
    except Exception as e:
        logger.error(f"检索失败: {str(e)}")
        return []

def get_llm():
    """获取大语言模型实例"""
    return ChatOllama(model=MODEL_NAME)

def generate_skill_summary(username, context):
    """生成技术能力总结"""
    if not context.strip():
        return { "prompt": "", 
                "summary": "未找到相关信息，无法生成技术能力总结。", 
                "context": context, 
                "model": MODEL_NAME}
    
    # 使用配置中的提示模板
    prompt_template = SKILL_ANALYSIS_PROMPT
    
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["username", "context"]
    )
    
    prompt_vars = {"username": username, "context": context}
    prompt_text = prompt.format(**prompt_vars)

    # 使用RunnableSequence方式
    llm = get_llm()
    chain = prompt | llm
    
    # 生成摘要
    try:
        raw_summary = chain.invoke({"username": username, "context": context})
        
        # 从ChatMessage或字符串中获取内容
        if hasattr(raw_summary, 'content'):
            raw_summary = raw_summary.content
        
        raw_summary_no_think = re.sub(r'<think>.*?</think>', '', raw_summary, flags=re.DOTALL).strip()
        # 高效的去重处理
        # 1. 按段落拆分
        paragraphs = [p.strip() for p in raw_summary_no_think.split("\n\n") if p.strip()]
        
        # 2. 创建去重后的段落列表
        unique_paragraphs = []
        seen_paragraphs = set()
        
        for paragraph in paragraphs:
            # 将段落转换为小写，并去除标点符号，用于更宽松的比较
            normalized = ''.join(c.lower() for c in paragraph if c.isalnum() or c.isspace())
            
            # 如果段落是重复的，跳过
            if normalized in seen_paragraphs:
                continue
                
            seen_paragraphs.add(normalized)
            unique_paragraphs.append(paragraph)
        
        # 3. 重新组合成文本
        clean_summary = "\n\n".join(unique_paragraphs)
        
        # 4. 清理格式问题 - 去除多余的列表标记
        clean_summary = re.sub(r'(\*\s+.+?\n\*\s+.+?)\n\*\s+', r'\1\n* ', clean_summary)
        
        # 返回包含模型名称的结果
        return {"summary": clean_summary, "model": MODEL_NAME}
    except Exception as e:
        logger.error(f"生成技术能力总结失败: {str(e)}")
        return {"summary": f"生成总结时发生错误: {str(e)}", "model": MODEL_NAME}

def generate_search_queries(query):
    """使用大语言模型扩展原始查询，生成更多相关查询"""
    prompt_template = PROMPT
    
    try:
        # 获取当前日期
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 创建提示模板
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["input_query", "date"]
        )
        
        # 使用RunnableSequence方式
        llm = get_llm()
        chain = prompt | llm
        
        # 生成查询
        result = chain.invoke({"input_query": query, "date": current_date})
        
        # 从ChatMessage或字符串中获取内容
        if hasattr(result, 'content'):
            result = result.content
            
        # 处理结果，拆分成多个查询
        queries = [q.strip() for q in result.strip().split("\n") if q.strip()]
        logger.info(f"为查询 '{query}' 生成了 {len(queries)} 个扩展查询")
        
        return queries
    except Exception as e:
        logger.error(f"生成查询失败: {str(e)}")
        return [query]  # 发生错误时返回原始查询 