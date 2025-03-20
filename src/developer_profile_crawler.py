import os
import re
import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urlparse
import json
from config import GITHUB_TOKEN, headers

logger = logging.getLogger(__name__)

def get_developer_profile(username):
    """获取开发者的GitHub个人资料信息"""
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        logger.error(f"获取开发者资料失败: {response.status_code}")
        return None
    
    data = response.json()
    return {
        "username": data.get("login"),
        "name": data.get("name"),
        "bio": data.get("bio"),
        "blog": data.get("blog"),
        "company": data.get("company"),
        "location": data.get("location"),
        "email": data.get("email"),
        "twitter_username": data.get("twitter_username"),
        "followers": data.get("followers"),
        "following": data.get("following"),
        "public_repos": data.get("public_repos"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "hireable": data.get("hireable")
    }

def get_developer_readme(username):
    """获取开发者的个人README信息（GitHub个人主页特殊仓库）"""
    url = f"https://api.github.com/repos/{username}/{username}/readme"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        logger.info(f"开发者没有个人README: {response.status_code}")
        return ""
    
    data = response.json()
    import base64
    content = base64.b64decode(data.get("content")).decode("utf-8")
    return content

def fetch_external_website(url, custom_headers=None):
    """抓取开发者的外部网站内容
    
    Args:
        url: 要抓取的网站URL
        custom_headers: 可选的自定义请求头，如果不提供则使用默认头
    """
    if not url or not url.startswith(('http://', 'https://')):
        return ""

    headers = custom_headers or {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    }
    
    try:
        logger.info(f"正在抓取网站: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"抓取外部网站失败: {url}, 状态码: {response.status_code}")
            return ""
        
        encoding = response.encoding
        if encoding.lower() == 'iso-8859-1':
            # 尝试从内容检测正确的编码
            encoding = response.apparent_encoding
            response.encoding = encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.extract()
            
        # 获取文本内容
        text = soup.get_text(separator='\n')
        
        # 清理文本（移除多余空行等）
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        logger.info(f"成功抓取网站内容，文本长度: {len(text)} 字符")
        return text
    except requests.exceptions.Timeout:
        logger.error(f"抓取外部网站超时: {url}")
        return ""
    except requests.exceptions.RequestException as e:
        logger.error(f"请求异常: {url}, 错误: {str(e)}")
        return ""
    except Exception as e:
        logger.error(f"抓取外部网站异常: {url}, 错误: {str(e)}")
        return ""

def get_developer_languages(username):
    """获取开发者常用的编程语言"""
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url, headers=headers, params={"per_page": 100})
    
    if response.status_code != 200:
        logger.error(f"获取开发者仓库失败: {response.status_code}")
        return {}
    
    repos = response.json()
    languages = {}
    
    for repo in repos:
        lang_url = repo["languages_url"]
        lang_response = requests.get(lang_url, headers=headers)
        
        if lang_response.status_code == 200:
            repo_languages = lang_response.json()
            for lang, bytes_count in repo_languages.items():
                if lang in languages:
                    languages[lang] += bytes_count
                else:
                    languages[lang] = bytes_count
    
    # 转换为百分比
    total_bytes = sum(languages.values())
    language_percentages = {}
    
    if total_bytes > 0:
        for lang, bytes_count in languages.items():
            percentage = (bytes_count / total_bytes) * 100
            language_percentages[lang] = round(percentage, 2)
    
    # 按百分比排序
    sorted_languages = {k: v for k, v in sorted(language_percentages.items(), key=lambda item: item[1], reverse=True)}
    return sorted_languages

def collect_developer_data(username):
    """收集开发者的所有相关数据"""
    profile_data = get_developer_profile(username)
    
    if not profile_data:
        return None
        
    data = {
        "profile": profile_data,
        "readme": get_developer_readme(username),
        "languages": get_developer_languages(username),
        "blog_content": ""
    }
    
    # 如果有博客或个人网站，抓取内容
    if profile_data.get("blog"):
        blog_url = profile_data["blog"]
        logger.info(f"开发者 {username} 提供了博客/网站: {blog_url}")
        data["blog_content"] = fetch_external_website(blog_url)
    
    return data 