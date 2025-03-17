import base64
from collections import Counter
import logging
import requests
from config import headers
import re


def analyze_language_culture_hints(username):
    """分析用户仓库中的语言和文化线索"""
    logger = logging.getLogger(__name__)
    logger.info(f"开始分析用户 '{username}' 的语言和文化线索")
    
    language_counter = Counter()
    readme_languages = Counter()
    bio_languages = Counter()
    issue_languages = Counter()
    
    # 语言特征模式
    language_patterns = {
        'Chinese': r'[\u4e00-\u9fff]+',  # 中文汉字
        'Japanese': r'[\u3040-\u309F\u30A0-\u30FF\u3400-\u4DBF]+',  # 日文假名和部分汉字
        'Korean': r'[\uAC00-\uD7AF\u1100-\u11FF]+',  # 韩文
        'Russian': r'[\u0400-\u04FF]+',  # 西里尔字母
        'Arabic': r'[\u0600-\u06FF]+',  # 阿拉伯文
        'Hindi': r'[\u0900-\u097F]+',  # 印地文
        'Thai': r'[\u0E00-\u0E7F]+',  # 泰文
        'Hebrew': r'[\u0590-\u05FF]+',  # 希伯来文
    }
    
    # 语言关键词
    language_keywords = {
        'Chinese': ['中国', '你好', '谢谢', '请', '我们', '什么', '为什么', '如何'],
        'Japanese': ['こんにちは', 'ありがとう', 'お願いします', '私たち', '何', 'なぜ', 'どうやって'],
        'Korean': ['안녕하세요', '감사합니다', '부탁합니다', '우리', '무엇', '왜', '어떻게'],
        'Russian': ['привет', 'спасибо', 'пожалуйста', 'мы', 'что', 'почему', 'как'],
        'Spanish': ['hola', 'gracias', 'por favor', 'nosotros', 'qué', 'por qué', 'cómo'],
        'French': ['bonjour', 'merci', 's\'il vous plaît', 'nous', 'quoi', 'pourquoi', 'comment'],
        'German': ['hallo', 'danke', 'bitte', 'wir', 'was', 'warum', 'wie'],
        'Portuguese': ['olá', 'obrigado', 'por favor', 'nós', 'o que', 'por que', 'como'],
        'Italian': ['ciao', 'grazie', 'per favore', 'noi', 'cosa', 'perché', 'come'],
    }
    
    try:
        # 1. 分析用户个人资料中的语言线索
        try:
            profile_url = f"https://api.github.com/users/{username}"
            profile_response = requests.get(profile_url, headers=headers, timeout=10)
            
            if profile_response.status_code == 200:
                profile = profile_response.json()
                bio = profile.get("bio", "")
                
                if bio:
                    logger.info(f"分析用户 '{username}' 的个人简介")
                    # 检测个人简介中的语言特征
                    for lang, pattern in language_patterns.items():
                        if re.search(pattern, bio):
                            bio_languages[lang] += 3  # 个人简介中的语言线索权重更高
                            logger.info(f"在用户 '{username}' 的个人简介中检测到 {lang} 语言")
                    
                    # 检测关键词
                    for lang, keywords in language_keywords.items():
                        for keyword in keywords:
                            if keyword.lower() in bio.lower():
                                bio_languages[lang] += 1
                                logger.info(f"在用户 '{username}' 的个人简介中检测到 {lang} 关键词: {keyword}")
        except Exception as e:
            logger.warning(f"分析用户 '{username}' 的个人资料时发生错误: {str(e)}")
        
        # 2. 分析用户仓库
        repos_url = f"https://api.github.com/users/{username}/repos"
        repos_response = requests.get(repos_url, headers=headers, timeout=10)
        
        if repos_response.status_code != 200:
            logger.warning(f"请求用户 '{username}' 的仓库列表失败，状态码: {repos_response.status_code}")
            return None
            
        repos = repos_response.json()
        logger.info(f"获取到用户 '{username}' 的仓库: {len(repos)} 个")
        
        for repo in repos:
            try:
                # 统计编程语言
                language = repo.get("language")
                if language:
                    language_counter[language] += 1
                    logger.info(f"仓库 '{repo['name']}' 的主要编程语言: {language}")
                
                # 分析仓库描述
                description = repo.get("description", "")
                if description:
                    for lang, pattern in language_patterns.items():
                        if re.search(pattern, description):
                            readme_languages[lang] += 2  # 描述中的语言线索权重较高
                            logger.info(f"在仓库 '{repo['name']}' 的描述中检测到 {lang} 语言")
                    
                # 分析README文件
                repo_name = repo["name"]
                readme_url = f"https://api.github.com/repos/{username}/{repo_name}/readme"
                readme_response = requests.get(readme_url, headers=headers, timeout=10)
                
                if readme_response.status_code == 200:
                    try:
                        readme_content = base64.b64decode(readme_response.json().get("content", "")).decode('utf-8')
                        
                        # 检测语言特征
                        for lang, pattern in language_patterns.items():
                            if re.search(pattern, readme_content):
                                readme_languages[lang] += 1
                                logger.info(f"在仓库 '{repo_name}' 的README中检测到 {lang} 语言")
                        
                        # 检测关键词
                        for lang, keywords in language_keywords.items():
                            for keyword in keywords:
                                if keyword.lower() in readme_content.lower():
                                    readme_languages[lang] += 0.5  # 关键词权重较低
                                    logger.debug(f"在仓库 '{repo_name}' 的README中检测到 {lang} 关键词")
                    except UnicodeDecodeError as e:
                        logger.warning(f"解码仓库 '{repo_name}' 的README内容时发生错误: {str(e)}")
                    except Exception as e:
                        logger.warning(f"处理仓库 '{repo_name}' 的README内容时发生错误: {str(e)}")
                
                # 3. 分析issue和PR评论中的语言（可选，API请求较多）
                try:
                    # 只分析最近的几个issue，避免过多API请求
                    issues_url = f"https://api.github.com/repos/{username}/{repo_name}/issues?creator={username}&state=all&per_page=5"
                    issues_response = requests.get(issues_url, headers=headers, timeout=10)
                    
                    if issues_response.status_code == 200:
                        issues = issues_response.json()
                        
                        for issue in issues:
                            issue_body = issue.get("body", "")
                            if issue_body:
                                for lang, pattern in language_patterns.items():
                                    if re.search(pattern, issue_body):
                                        issue_languages[lang] += 1
                                        logger.info(f"在用户 '{username}' 的issue中检测到 {lang} 语言")
                except Exception as e:
                    logger.debug(f"分析仓库 '{repo_name}' 的issue时发生错误: {str(e)}")
                    
            except Exception as e:
                logger.warning(f"处理仓库 '{repo.get('name', 'unknown')}' 时发生错误: {str(e)}")
                continue
        
        # 合并所有语言线索，加权计算
        combined_languages = Counter()
        for lang, count in readme_languages.items():
            combined_languages[lang] += count
        
        for lang, count in bio_languages.items():
            combined_languages[lang] += count * 2  # 个人简介权重更高
            
        for lang, count in issue_languages.items():
            combined_languages[lang] += count * 1.5  # issue评论权重中等
        
        result = {
            "programming_languages": language_counter.most_common(5),
            "readme_languages": readme_languages.most_common(3),
            "bio_languages": bio_languages.most_common(3),
            "issue_languages": issue_languages.most_common(3),
            "combined_languages": combined_languages.most_common(3)
        }
        
        logger.info(f"完成用户 '{username}' 的语言文化分析，找到 {len(language_counter)} 种编程语言，{len(combined_languages)} 种自然语言")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"分析用户 '{username}' 的语言文化线索时发生网络错误: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"分析用户 '{username}' 的语言文化线索时发生错误: {str(e)}")
        return None
