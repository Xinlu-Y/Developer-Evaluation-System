import logging
import requests
import re
from collections import defaultdict, Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string
from config import headers

# 下载必要的NLTK资源
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

logger = logging.getLogger(__name__)

# 技术领域映射表
DOMAIN_MAPPINGS = {
    # 前端技术
    'frontend': ['react', 'vue', 'angular', 'svelte', 'javascript', 'typescript', 'html', 'css', 'sass', 'less', 
                'webpack', 'vite', 'rollup', 'nextjs', 'nuxt', 'redux', 'vuex', 'tailwind', 'bootstrap', 'ui'],
    
    # 后端技术
    'backend': ['node', 'express', 'django', 'flask', 'fastapi', 'spring', 'springboot', 'rails', 'laravel', 'php',
               'golang', 'rust', 'java', 'kotlin', 'scala', 'graphql', 'rest', 'api', 'serverless', 'microservice'],
    
    # 移动开发
    'mobile': ['android', 'ios', 'swift', 'flutter', 'reactnative', 'xamarin', 'mobile', 'app', 'cordova',
              'ionic', 'kotlin', 'objective-c'],
    
    # 数据科学
    'data-science': ['datascience', 'machinelearning', 'ml', 'ai', 'deeplearning', 'tensorflow', 'pytorch', 'pandas',
                    'numpy', 'scipy', 'scikit-learn', 'jupyter', 'statistics', 'analytics', 'bigdata'],
    
    # 大语言模型
    'llm': ['llm', 'nlp', 'gpt', 'bert', 'transformer', 'language-model', 'openai', 'langchain', 'chatbot',
           'prompt-engineering', 'semantic', 'embedding', 'text-generation', 'huggingface', 'rag'],
    
    # 数据库
    'database': ['database', 'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'neo4j', 'cassandra',
                'dynamodb', 'orm', 'jdbc', 'nosql', 'firebase', 'supabase'],
    
    # DevOps与云计算
    'devops': ['devops', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'cicd', 'jenkins', 'terraform', 'ansible',
              'monitoring', 'logging', 'cloud', 'serverless', 'infrastructure', 'github-actions', 'gitlab-ci'],
    
    # 游戏开发
    'gamedev': ['game', 'gamedev', 'unity', 'unreal', 'threejs', 'webgl', 'godot', 'gamification', 'simulator',
               'graphics', 'ar', 'vr'],
    
    # 安全
    'security': ['security', 'encryption', 'cybersecurity', 'authentication', 'authorization', 'jwt', 'oauth',
                'cryptography', 'privacy', 'pentesting', 'vulnerability', 'firewall', 'blockchain'],
    
    # 区块链
    'blockchain': ['blockchain', 'ethereum', 'solidity', 'web3', 'cryptocurrency', 'bitcoin', 'nft', 'defi',
                  'smart-contract', 'wallet', 'token', 'consensus']
}

# 反向映射（关键词到领域）
KEYWORD_TO_DOMAIN = {}
for domain, keywords in DOMAIN_MAPPINGS.items():
    for keyword in keywords:
        KEYWORD_TO_DOMAIN[keyword] = domain

# 停用词
TECH_STOP_WORDS = set(['app', 'application', 'system', 'tool', 'toolkit', 'framework', 'library', 'platform', 
                      'project', 'code', 'demo', 'example', 'test', 'sample', 'implementation'])
STOP_WORDS = set(stopwords.words('english')).union(TECH_STOP_WORDS)

def extract_keywords(text):
    """从文本中提取技术关键词"""
    if not text:
        return []
    
    # 转小写，去除标点
    text = text.lower()
    text = re.sub(f'[{string.punctuation}]', ' ', text)
    
    # 分词
    tokens = word_tokenize(text)
    
    # 过滤停用词
    filtered_tokens = [word for word in tokens if word not in STOP_WORDS and len(word) > 2]
    
    return filtered_tokens

def map_keywords_to_domains(keywords):
    """将关键词映射到标准化的技术领域"""
    domain_counts = Counter()
    
    for keyword in keywords:
        if keyword in KEYWORD_TO_DOMAIN:
            domain = KEYWORD_TO_DOMAIN[keyword]
            domain_counts[domain] += 1
        else:
            # 尝试部分匹配
            for domain, domain_keywords in DOMAIN_MAPPINGS.items():
                if any(keyword in domain_keyword or domain_keyword in keyword for domain_keyword in domain_keywords):
                    domain_counts[domain] += 0.5  # 部分匹配给予较低的权重
                    break
    
    return domain_counts

def analyze_repository(repo_data):
    """分析单个仓库，返回领域权重"""
    domain_weights = Counter()
    
    # 1. 分析仓库名称
    if repo_data.get('repo_name'):
        name_keywords = extract_keywords(repo_data['repo_name'])
        name_domains = map_keywords_to_domains(name_keywords)
        for domain, count in name_domains.items():
            domain_weights[domain] += count * 1.5  # 仓库名称的权重较高
    
    # 2. 分析仓库描述
    if repo_data.get('repo_description'):
        desc_keywords = extract_keywords(repo_data['repo_description'])
        desc_domains = map_keywords_to_domains(desc_keywords)
        for domain, count in desc_domains.items():
            domain_weights[domain] += count
    
    # 3. 考虑编程语言权重
    if repo_data.get('language'):
        lang = repo_data['language'].lower()
        for domain, keywords in DOMAIN_MAPPINGS.items():
            if lang in keywords:
                domain_weights[domain] += 2  # 编程语言是强指标
                break
    
    # 4. 根据Star数量调整权重
    stars = repo_data.get('Star', 0)
    star_multiplier = 1.0
    if stars > 1000:
        star_multiplier = 3.0
    elif stars > 100:
        star_multiplier = 2.0
    elif stars > 10:
        star_multiplier = 1.5
    
    for domain in domain_weights:
        domain_weights[domain] *= star_multiplier
    
    return domain_weights

def get_repository_languages(username, repo_name):
    """获取仓库使用的编程语言及其比例"""
    try:
        url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"获取仓库 {username}/{repo_name} 语言信息失败，状态码: {response.status_code}")
            return {}
            
        languages = response.json()
        total = sum(languages.values())
        
        # 计算每种语言的百分比
        language_percentages = {lang: (count / total) * 100 for lang, count in languages.items()}
        return language_percentages
        
    except Exception as e:
        logger.error(f"获取仓库 {username}/{repo_name} 语言信息时发生错误: {str(e)}")
        return {}

def get_repository_topics(username, repo_name):
    """获取仓库的主题标签"""
    try:
        url = f"https://api.github.com/repos/{username}/{repo_name}/topics"
        # 需要特殊的Accept头部
        headers_with_topics = headers.copy()
        headers_with_topics['Accept'] = 'application/vnd.github.mercy-preview+json'
        
        response = requests.get(url, headers=headers_with_topics, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"获取仓库 {username}/{repo_name} 主题标签失败，状态码: {response.status_code}")
            return []
            
        return response.json().get('names', [])
        
    except Exception as e:
        logger.error(f"获取仓库 {username}/{repo_name} 主题标签时发生错误: {str(e)}")
        return []

def enrich_repo_data(username, repo_data):
    """增强仓库数据，添加语言和主题信息"""
    repo_name = repo_data.get('repo_name')
    if not repo_name:
        return repo_data
    
    # 复制原数据以避免修改
    enriched_data = dict(repo_data)
    
    # 添加语言信息
    languages = get_repository_languages(username, repo_name)
    if languages:
        # 找出最主要的语言
        main_language = max(languages.items(), key=lambda x: x[1])[0]
        enriched_data['language'] = main_language
        enriched_data['language_percentages'] = languages
    
    # 添加主题标签
    topics = get_repository_topics(username, repo_name)
    if topics:
        enriched_data['topics'] = topics
    
    return enriched_data

def get_developer_domains(username, repositories=None):
    """
    分析开发者的技术领域
    
    参数:
    - username: 开发者用户名
    - repositories: 可选，预先获取的仓库数据列表
    
    返回:
    - 包含领域与评分的字典
    """
    logger.info(f"开始分析开发者 '{username}' 的技术领域")
    
    # 如果没有提供仓库数据，尝试获取
    if not repositories:
        from user_profile import get_user_repos
        try:
            repositories = get_user_repos(username)
            logger.info(f"获取到开发者 '{username}' 的 {len(repositories)} 个仓库")
        except Exception as e:
            logger.error(f"获取开发者 '{username}' 的仓库信息失败: {str(e)}")
            return {}
    
    if not repositories:
        logger.warning(f"开发者 '{username}' 没有可分析的仓库")
        return {}
    
    # 只分析开发者拥有的仓库
    owner_repos = [repo for repo in repositories if repo.get("repo_type") == "owner"]
    
    # 对每个仓库进行数据增强
    enriched_repos = []
    for repo in owner_repos:
        try:
            enriched_repo = enrich_repo_data(username, repo)
            enriched_repos.append(enriched_repo)
        except Exception as e:
            logger.warning(f"增强仓库 {repo.get('repo_name')} 数据时出错: {str(e)}")
            enriched_repos.append(repo)  # 使用原始数据
    
    # 累积各领域的权重
    domain_weights = Counter()
    
    for repo in enriched_repos:
        repo_domains = analyze_repository(repo)
        # 根据仓库星数调整权重
        star_weight = 1 + (repo.get('Star', 0) / 100)  # Star越多权重越大
        for domain, weight in repo_domains.items():
            domain_weights[domain] += weight * star_weight
    
    # 如果没有检测到任何领域，返回空
    if not domain_weights:
        logger.warning(f"未能检测到开发者 '{username}' 的技术领域")
        return {}
    
    # 归一化权重值到0-100
    max_weight = max(domain_weights.values())
    if max_weight > 0:
        normalized_domains = {
            domain: round((weight / max_weight) * 100, 1)
            for domain, weight in domain_weights.items()
        }
    else:
        normalized_domains = {domain: 0.0 for domain in domain_weights}
    
    # 选择得分最高的5个领域
    top_domains = dict(sorted(normalized_domains.items(), key=lambda x: x[1], reverse=True)[:5])
    
    logger.info(f"分析完成，开发者 '{username}' 的主要技术领域: {top_domains}")
    return top_domains 