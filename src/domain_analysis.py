import logging
import requests
import re
from collections import defaultdict, Counter
import difflib
import spacy
import string
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
import math
from typing import Dict, List, Any, Tuple

try:
    from config import headers
except ModuleNotFoundError:
    headers = {
        'User-Agent': 'Developer-Evaluation-System',
        'Accept': 'application/vnd.github.v3+json'
    }
    logging.warning("未找到config模块，使用默认headers")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 加载spaCy模型
try:
    nlp = spacy.load("en_core_web_sm")
    logging.info("成功加载spaCy模型 'en_core_web_sm'")
except OSError:
    logging.error("spaCy模型未找到。请先运行: python -m spacy download en_core_web_sm")
    nlp = spacy.blank("en")
    logging.warning("使用空白spaCy模型作为后备方案")

logger = logging.getLogger(__name__)

# --- 多层级领域定义 ---
DOMAIN_HIERARCHY = {
    'Software Development': {
        'Frontend': [
            'React', 'Vue.js', 'Angular', 'JavaScript', 'TypeScript', 'HTML5', 'CSS3',
            'Tailwind CSS', 'Bootstrap', 'Sass', 'Redux', 'Webpack', 'Vite', 'Next.js',
            'Nuxt.js', 'PWA', 'WebAssembly', 'SVG', 'D3.js', 'Three.js', 'jQuery'
        ],
        'Backend': [
            'Node.js', 'Express', 'Django', 'Flask', 'Spring Boot', 'Laravel', 'Rails',
            'ASP.NET', 'FastAPI', 'GraphQL', 'REST API', 'gRPC', 'OAuth', 'JWT',
            'Microservices', 'Serverless', 'WebSockets', 'RabbitMQ', 'Kafka', 'Redis'
        ],
        'Mobile': [
            'iOS', 'Android', 'Swift', 'Kotlin', 'React Native', 'Flutter', 'Xamarin',
            'Ionic', 'SwiftUI', 'Jetpack Compose', 'ARKit', 'Firebase', 'CoreML',
            'Mobile UI', 'Push Notifications', 'AppClip'
        ],
        'GameDev': [
            'Unity', 'Unreal', 'Godot', 'Cocos2d', 'Phaser', 'Game AI', 'Physics Engine',
            'Shaders', 'Procedural Gen', 'Networking', 'VFX', 'Animation', 'C#', 'C++',
            'Blender', 'Collision Detection', '2D Games', '3D Games'
        ],
        'Cross-platform': [
            'Electron', 'Tauri', 'PWA', 'React Native', 'Flutter', 'Qt', 'MAUI',
            'UWP', 'NativeScript', 'Capacitor', 'Cordova', 'Xamarin'
        ]
    },

    'AI': {
        'Machine Learning': [
            'scikit-learn', 'XGBoost', 'LightGBM', 'CatBoost', 'SVM', 'Random Forest',
            'Neural Networks', 'Feature Engineering', 'Hyperparam Tuning', 'AutoML',
            'Regression', 'Classification', 'Clustering', 'Anomaly Detection',
            'Bayesian Methods', 'Time Series'
        ],
        'NLP': [
            'BERT', 'GPT', 'LLM', 'Transformers', 'Word2Vec', 'spaCy', 'NLTK',
            'HuggingFace', 'NER', 'Sentiment Analysis', 'Machine Translation',
            'Text Gen', 'QA', 'Summarization', 'Topic Modeling', 'RAG', 'Tokenization'
        ],
        'Computer Vision': [
            'OpenCV', 'YOLO', 'CNN', 'GANs', 'Object Detection', 'Segmentation',
            'Face Recognition', 'Pose Estimation', 'OCR', 'Medical Imaging', 'AR',
            '3D Reconstruction', 'Transfer Learning', 'Image Gen', 'Feature Extraction'
        ],
        'Reinforcement Learning': [
            'Q-Learning', 'DQN', 'PPO', 'DDPG', 'A3C', 'OpenAI Gym', 'MuJoCo',
            'Multi-agent', 'Policy Gradient', 'Actor-Critic', 'MDP', 'Sim2Real'
        ],
        'Generative AI': [
            'Stable Diffusion', 'DALL-E', 'Midjourney', 'GANs', 'VAE', 'Diffusion Models',
            'Text-to-Image', 'Text-to-Video', 'Voice Synthesis', 'Music Gen',
            'Style Transfer', 'Inpainting', 'Promptcraft', 'ControlNet', 'LoRA'
        ]
    },

    'Data Science': {
        'Data Analysis': [
            'Pandas', 'NumPy', 'SQL', 'R', 'EDA', 'Statistical Analysis', 'Hypothesis Testing',
            'A/B Testing', 'Time Series', 'Regression Analysis', 'Excel', 'Feature Engineering',
            'Sampling Methods', 'Bayesian Analysis'
        ],
        'Visualization': [
            'Matplotlib', 'Seaborn', 'Plotly', 'D3.js', 'Tableau', 'Power BI', 'Grafana',
            'Kibana', 'Network Graphs', 'Dashboards', 'Geospatial Vis', 'Infographics',
            'ECharts', 'Heatmaps', 'Visual Storytelling'
        ],
        'Big Data': [
            'Hadoop', 'Spark', 'Flink', 'MapReduce', 'Hive', 'Presto', 'Kafka',
            'Druid', 'Storm', 'Beam', 'Distributed Computing', 'Columnar Storage',
            'Batch Processing', 'Stream Processing'
        ],
        'Data Engineering': [
            'ETL', 'Airflow', 'dbt', 'Dagster', 'Data Lake', 'Snowflake',
            'Data Warehouse', 'Data Pipeline', 'Schema Design', 'Data Governance',
            'Metadata Management', 'Delta Lake', 'Data Quality', 'Data Lineage'
        ]
    },

    'Systems & Infrastructure': {
        'Cloud': [
            'AWS', 'Azure', 'GCP', 'Cloud Native', 'Serverless', 'IaaS', 'PaaS', 'SaaS',
            'Cloud Security', 'Cloud Storage', 'Hybrid Cloud', 'Cloud Migration', 'K8s'
        ],
        'DevOps': [
            'CI/CD', 'Jenkins', 'GitHub Actions', 'Docker', 'Kubernetes', 'Terraform',
            'Ansible', 'Infrastructure as Code', 'Monitoring', 'Logging', 'GitOps', 'SRE'
        ],
        'Systems Programming': [
            'C', 'C++', 'Rust', 'Go', 'Assembly', 'Linux Kernel', 'Embedded Systems',
            'Device Drivers', 'Concurrency', 'Memory Management', 'IPC', 'POSIX',
            'File Systems', 'Low-level Optimization'
        ],
        'Databases': [
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch', 'Cassandra',
            'SQL Server', 'SQLite', 'DynamoDB', 'Indexing', 'Query Optimization',
            'Sharding', 'Replication', 'ACID'
        ],
        'Networking': [
            'TCP/IP', 'HTTP', 'gRPC', 'WebSockets', 'DNS', 'QUIC', 'VPN', 'Proxy',
            'CDN', 'Load Balancing', 'Network Protocols', 'Firewall', 'IPv6', 'Packet Analysis'
        ]
    },

    'Cybersecurity': {
        'AppSec': ['OWASP', 'XSS', 'CSRF', 'SQL Injection', 'JWT', 'OAuth', 'SAST', 'DAST'],
        'Network Security': ['Firewall', 'IDS', 'IPS', 'VPN', 'Wireshark', 'DDoS', 'SIEM'],
        'Cryptography': ['RSA', 'AES', 'SSL/TLS', 'PKI', 'Blockchain', 'Quantum Crypto', 'ZKP'],
        'SecOps': ['Incident Response', 'Threat Hunting', 'Vulnerability Mgmt', 'SOC', 'Forensics']
    }
}


# --- 构建映射表 ---
L3_TO_L2 = {}
L2_TO_L1 = {}
for lvl1, sub in DOMAIN_HIERARCHY.items():
    for lvl2, kws in sub.items():
        L2_TO_L1[lvl2] = lvl1
        for kw in kws:
            L3_TO_L2[kw.lower()] = lvl2

# 可选：正则映射列表
L3_REGEX = []  # e.g. [(re.compile(pattern), 'Some Level3'), ...]

class VectorSemanticExtension:
    """技术关键词的向量化语义扩展"""
    def __init__(self, model_name='all-MiniLM-L6-v2', similarity_threshold=0.75):
        self.similarity_threshold = similarity_threshold
        try:
            self.model = SentenceTransformer(model_name)
        except Exception:
            logging.warning("SentenceTransformer模型加载失败，向量化匹配不可用")
            self.model = None
        self.keyword_vectors = {}
        self.keyword_to_domain = {}
        self.initialized = False

    def build_vector_database(self, domain_hierarchy):
        if not self.model: return
        all_keywords, mapping = [], {}
        for lvl1, subs in domain_hierarchy.items():
            for lvl2, kws in subs.items():
                for kw in kws:
                    key = kw.lower()
                    all_keywords.append(key)
                    mapping[key] = (lvl1, lvl2, kw)
        vectors = self.model.encode(all_keywords, show_progress_bar=False)
        for kw, vec in zip(all_keywords, vectors):
            self.keyword_vectors[kw] = vec
        self.keyword_to_domain = mapping
        self.initialized = True

    def find_similar_keywords(self, query, top_n=3):
        if not self.initialized: return []
        qv = self.model.encode([query.lower()])[0]
        sims = {kw: cosine_similarity([qv],[v])[0][0] 
                for kw,v in self.keyword_vectors.items()}
        return sorted(((k,v) for k,v in sims.items() if v>=self.similarity_threshold),
                      key=lambda x: x[1], reverse=True)[:top_n]

    def match_domain_semantic(self, keyword):
        if not self.initialized: return None
        matches = self.find_similar_keywords(keyword, 1)
        if not matches: return None
        kw, sim = matches[0]
        lvl1,lvl2,_ = self.keyword_to_domain[kw]
        weight = sim * 0.8
        return lvl1, lvl2, kw, weight

def match_domain_for_keyword_extended(kw, vector_matcher):
    # 先尝试原有精确匹配
    exact = match_domain_for_keyword(kw)
    if exact: return exact
    # 否则尝试语义匹配
    if vector_matcher and vector_matcher.initialized:
        return vector_matcher.match_domain_semantic(kw)
    return None

def initialize_vector_matcher():
    matcher = VectorSemanticExtension()
    matcher.build_vector_database(DOMAIN_HIERARCHY)
    return matcher

# 在模块加载时构建一次全局 matcher
VECTOR_MATCHER = initialize_vector_matcher()

class WeightNormalizer:
    def __init__(self):
        self.document_frequencies: Counter = Counter()
        self.total_documents: int = 0
        self.initialized: bool = False
        self.idf_cache: Dict[str,float] = {}

    def build_document_frequencies(self, repos: List[Dict[str,Any]]):
        logger.info("开始构建文档频率统计 …")
        self.document_frequencies.clear()
        self.total_documents = len(repos)
        for repo in repos:
            kws = set()
            if repo.get('repo_name'):
                kws |= set(extract_keywords(repo['repo_name']))
            if repo.get('repo_description'):
                kws |= set(extract_keywords(repo['repo_description']))
            kws |= {t.lower() for t in repo.get('topics',[])}
            for kw in kws:
                self.document_frequencies[kw] += 1
        total = max(1, self.total_documents)
        for kw, df in self.document_frequencies.items():
            self.idf_cache[kw] = math.log((total+1)/(df+1)) + 1
        self.initialized = True
        logger.info(f"文档频率统计完成: {self.total_documents} 个仓库, {len(self.idf_cache)} 个关键词")

    def get_tfidf_weight(self, keyword: str, tf: int = 1) -> float:
        if not self.initialized:
            return 1.0
        idf = self.idf_cache.get(keyword.lower(), math.log((self.total_documents+1)/1)+1)
        return tf * idf

    @staticmethod
    def apply_softmax(scores: Dict[str,float], temperature: float = 1.0) -> Dict[str,float]:
        if not scores:
            return {}
        items, vals = zip(*scores.items())
        arr = np.array(vals) / temperature
        exp = np.exp(arr - np.max(arr))
        sm = exp / np.sum(exp)
        # 添加保底值，避免得分为0导致展示异常
        return {items[i]: max(float(sm[i]), 0.001) for i in range(len(items))}


# 信号源与层级权重
SIGNAL_WEIGHTS = {
    'repo_name': 1.0,
    'repo_description': 1.5,
    'language': 0.8,
    'topics': 2.0
}
LEVEL_WEIGHTS = {
    'level3_exact': 1.0,
    'level3_partial': 0.5,
    'topic': 0.2,
    'language': 0.1
}

# 技术相关的停用词
TECH_STOP_WORDS = set(['app', 'application', 'system', 'tool', 'toolkit', 'framework', 'library', 'platform', 
                      'project', 'code', 'demo', 'example', 'test', 'sample', 'implementation', 'introduction',
                      'solution', 'development', 'template', 'boilerplate', 'starter', 'package', 'module'])


# 语言与领域关联表 - 一种语言可以关联到多个技术领域
LANGUAGE_TO_DOMAINS = {
    'javascript': ['frontend', 'backend', 'mobile'],
    'typescript': ['frontend', 'backend', 'mobile'],
    'python': ['backend', 'data-science', 'llm', 'computer-vision'],
    'java': ['backend', 'mobile', 'systems'],
    'kotlin': ['mobile', 'backend'],
    'swift': ['mobile'],
    'c#': ['gamedev', 'backend', 'systems'],
    'c++': ['systems', 'gamedev', 'graphics'],
    'c': ['systems', 'embedded', 'graphics'],
    'rust': ['systems', 'backend', 'blockchain'],
    'go': ['backend', 'systems', 'devops'],
    'php': ['backend', 'web'],
    'ruby': ['backend', 'web'],
    'dart': ['mobile'],
    'scala': ['backend', 'data-science'],
    'solidity': ['blockchain'],
    'r': ['data-science', 'statistics'],
    'matlab': ['data-science', 'engineering'],
    'shell': ['devops', 'systems'],
    'powershell': ['devops', 'systems'],
    'sql': ['database'],
    'html': ['frontend'],
    'css': ['frontend'],
    'glsl': ['graphics', 'gamedev'],
    'hlsl': ['graphics', 'gamedev'],
    'assembly': ['systems', 'embedded']
}

# --- 规则引擎函数 ---
def match_domain_for_keyword(kw):
    key = kw.lower()
    # 1) 完全匹配 Level3
    if key in L3_TO_L2:
        l2 = L3_TO_L2[key]
        return L2_TO_L1[l2], l2, key, LEVEL_WEIGHTS['level3_exact']
    # 2) 部分匹配 / 编辑距离
    candidate = difflib.get_close_matches(key, L3_TO_L2.keys(), n=1, cutoff=0.8)
    if candidate:
        l2 = L3_TO_L2[candidate[0]]
        return L2_TO_L1[l2], l2, candidate[0], LEVEL_WEIGHTS['level3_partial']
    # 3) 正则匹配
    for pattern, lvl3 in L3_REGEX:
        if pattern.search(key):
            l2 = L3_TO_L2.get(lvl3.lower())
            return L2_TO_L1[l2], l2, lvl3.lower(), LEVEL_WEIGHTS['level3_partial']
    return None

# --- 文本提取关键词 ---
def extract_keywords(text):
    if not text:
        return []
    doc = nlp(text.lower())
    tokens = [t.text for t in doc if not t.is_stop and not t.is_punct and len(t.text)>2]
    return list(set(tokens))

# --- 映射关键词到各层级领域 ---
def map_keywords_to_domains(keywords, signal):
    l1_scores = Counter()
    l2_scores = Counter()
    l3_scores = Counter()
    for kw in keywords:
        m = match_domain_for_keyword_extended(kw, VECTOR_MATCHER)
        if m:
            lvl1, lvl2, lvl3, w = m
            weight = SIGNAL_WEIGHTS[signal] * w
            l1_scores[lvl1] += weight
            l2_scores[lvl2] += weight
            l3_scores[lvl3] += weight
    return l1_scores, l2_scores, l3_scores

import logging
from collections import Counter
from typing import Tuple

logger = logging.getLogger(__name__)

def analyze_repository_with_weights(repo,
                                    weight_normalizer: WeightNormalizer,
                                    apply_tfidf=True) -> Tuple[Counter, Counter, Counter]:
    name_kws = extract_keywords(repo.get('repo_name',''))
    desc_kws = extract_keywords(repo.get('repo_description',''))
    all_kws = name_kws + desc_kws + repo.get('repo_topics', [])
    tf_counts = Counter(all_kws)

    total_l1, total_l2, total_l3 = Counter(), Counter(), Counter()
    print("DEBUG: repo['repo_topics'] =", repo.get('repo_topics', '不存在'))
    print("DEBUG: repo['repo_languages'] =", repo.get('repo_languages', '不存在'))

    # 用于调试的结构，记录每个信号源的明细
    contributions = {
        'repo_name': [],
        'repo_description': [],
        'topics': [],
        'language': []
    }

    # 1) 名称 & 描述
    for kws, sig in [(name_kws,'repo_name'), (desc_kws,'repo_description')]:
        for kw in kws:
            m = match_domain_for_keyword_extended(kw, VECTOR_MATCHER)
            if not m: 
                continue
            lvl1, lvl2, lvl3, base_w = m
            w = SIGNAL_WEIGHTS[sig] * base_w
            if apply_tfidf and weight_normalizer.initialized:
                w *= weight_normalizer.get_tfidf_weight(kw, tf_counts[kw])

            total_l1[lvl1] += w
            total_l2[lvl2] += w
            total_l3[lvl3] += w

            # 记录调试信息
            contributions[sig].append({
                'kw': kw,
                'mapped': (lvl1, lvl2, lvl3),
                'weight': round(w, 4)
            })

    # 2) topics
    for t in repo.get('repo_topics', []):
        m = match_domain_for_keyword_extended(t, VECTOR_MATCHER)
        if not m:
            continue
        lvl1, lvl2, lvl3, base_w = m
        w = SIGNAL_WEIGHTS['topics'] * base_w
        if apply_tfidf and weight_normalizer.initialized:
            w *= weight_normalizer.get_tfidf_weight(t, tf_counts[t])

        total_l1[lvl1] += w
        total_l2[lvl2] += w
        total_l3[lvl3] += w

        contributions['topics'].append({
            'topic': t,
            'mapped': (lvl1, lvl2, lvl3),
            'weight': round(w, 4)
        })

    # 3) language
    langs = repo.get('repo_languages', [])
    if isinstance(langs, str):
        langs = [langs]

    for lang in langs:
        lang = lang.lower()
        tfidf_lang = 1.0
        if apply_tfidf and weight_normalizer.initialized:
            tfidf_lang = weight_normalizer.get_tfidf_weight(lang, 1)

        for lvl2 in LANGUAGE_TO_DOMAINS.get(lang, []):
            lvl1 = L2_TO_L1.get(lvl2)
            base_w = LEVEL_WEIGHTS['language']
            w = SIGNAL_WEIGHTS['language'] * base_w * tfidf_lang

            if lvl1:
                total_l1[lvl1] += w
            total_l2[lvl2] += w

            contributions['language'].append({
                'language': lang,
                'mapped': (lvl1, lvl2),
                'weight': round(w, 4)
            })

    logger.info(f"仓库 [{repo.get('repo_name')}] 信号源贡献明细：")
    for sig, entries in contributions.items():
        if not entries:
            logger.info(f"  - {sig}: （无匹配项）")
            continue
        logger.info(f"  - {sig}:")
        for e in entries:
            if sig == 'language':
                logger.info(f"      · {e['language']} → L1={e['mapped'][0]}, L2={e['mapped'][1]}, w={e['weight']}")
            else:
                key = e.get('kw') or e.get('topic')
                logger.info(f"      · “{key}” → L1={e['mapped'][0]}, L2={e['mapped'][1]}, L3={e['mapped'][2]}, w={e['weight']}")

    return total_l1, total_l2, total_l3



# --- 主分析函数 ---
def get_developer_domains_weighted(username: str,
                                  owner_repos: List[Dict[str,Any]],
                                  apply_tfidf: bool = True,
                                  apply_softmax: bool = True,
                                  softmax_temp: float = 0.5
) -> List[Dict[str,Any]]:
    normalizer = WeightNormalizer()
    if apply_tfidf:
        normalizer.build_document_frequencies(owner_repos)
    agg_l1 = Counter(); agg_l2 = Counter(); agg_l3 = Counter()
    # 各仓库分析与本地归一化
    for repo in owner_repos:
        l1,l2,l3 = analyze_repository_with_weights(repo, normalizer, apply_tfidf)
        def norm(c):
            if not c: return {}
            m = max(c.values()); return {k: v/m for k,v in c.items()}
        nl1,nl2,nl3 = norm(l1), norm(l2), norm(l3)
        agg_l1.update(nl1); agg_l2.update(nl2); agg_l3.update(nl3)
    # 最终 Softmax 归一化
    if apply_softmax:
        agg_l1 = WeightNormalizer.apply_softmax(agg_l1, softmax_temp)
        agg_l2 = WeightNormalizer.apply_softmax(agg_l2, softmax_temp)
        agg_l3 = WeightNormalizer.apply_softmax(agg_l3, softmax_temp)
    # 转化为百分比
    def to_percent(c):
        if not c:
            return {}
        m = max(c.values()) if c else 1
        return {k: max(round(v / m * 100, 1), 0.1) for k, v in c.items()}
    normalized_l1 = to_percent(agg_l1)
    normalized_l2 = to_percent(agg_l2)
    normalized_l3_flat = to_percent(agg_l3)
    # 分组 & 构建树形结构
    grouped_l3 = defaultdict(dict)
    for lvl3_name, score in normalized_l3_flat.items():
        lvl2_name = L3_TO_L2.get(lvl3_name.lower())
        if lvl2_name:
            grouped_l3[lvl2_name][lvl3_name] = score
    hierarchy = []
    for lvl1_name, lvl1_score in normalized_l1.items():
        node1 = {"name": lvl1_name, "score": lvl1_score, "children": []}
        for lvl2_name, lvl2_score in normalized_l2.items():
            if L2_TO_L1.get(lvl2_name)==lvl1_name:
                node2 = {"name": lvl2_name, "score": lvl2_score, "children": []}
                for lvl3_name, lvl3_score in grouped_l3.get(lvl2_name,{}).items():
                    node2["children"].append({"name": lvl3_name, "score": lvl3_score})
                node1["children"].append(node2)
        hierarchy.append(node1)
    return hierarchy


# 将 numpy 类型转换为标准 Python 类型（递归转换）
def convert_numpy(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    elif isinstance(obj, np.float32) or isinstance(obj, np.float64):
        return float(obj)
    elif isinstance(obj, np.int32) or isinstance(obj, np.int64):
        return int(obj)
    else:
        return obj

if __name__ == "__main__":
    logging.getLogger(__name__).setLevel(logging.DEBUG)
    
    # 测试数据 - 模拟的仓库数据
    test_repositories = [
        {
            "repo_type": "owner",
            "repo_name": "vue-dashboard",
            "repo_description": "基于Vue3 + Vite构建的企业级管理后台模板",
            "repo_languages": "JavaScript",
            "repo_topics": ["vue", "vite", "admin-dashboard"]
        },
        {
            "repo_type": "owner",
            "repo_name": "flask_app_template",
            "repo_description": "A simple flask-based microservice API starter project",
            "repo_languages": "Python",
            "repo_topics": ["flask", "rest", "microservice"]
        },
        {
            "repo_type": "owner",
            "repo_name": "llm-evaluator",
            "repo_description": "Using transformer-based LLMs for sentiment classification and QA tasks.",
            "repo_languages": "Python",
            "repo_topics": ["llm", "transformers", "huggingface"]
        },
        {
            "repo_type": "owner",
            "repo_name": "open-vision",
            "repo_description": "Real-time object detection with yolov5 and OpenCV",
            "repo_languages": "Python",
            "repo_topics": ["opencv", "object-detection", "yolo"]
        },
        {
            "repo_type": "owner",
            "repo_name": "qt_ui_generator",
            "repo_description": "Cross-platform GUI generator built with Qt6 and Python.",
            "repo_languages": "C++",
            "repo_topics": ["qt", "cross-platform", "gui"]
        },
        {
            "repo_type": "owner",
            "repo_name": "data-analyse-toolkit",
            "repo_description": "EDA and visualization using pandas, seaborn, and matplotlib.",
            "repo_languages": "Python",
            "repo_topics": ["eda", "visualization", "matplotlib"]
        },
        {
            "repo_type": "owner",
            "repo_name": "secure-web-auth",
            "repo_description": "OAuth2 + JWT authentication for single-page apps.",
            "repo_languages": "JavaScript",
            "repo_topics": ["oauth", "jwt", "web-security"]
        },
        {
            "repo_type": "owner",
            "repo_name": "gameai-unity",
            "repo_description": "Exploring reinforcement learning with Unity ML-Agents toolkit",
            "repo_languages": "C#",
            "repo_topics": ["unity", "reinforcement-learning", "ml-agents"]
        },
        {
            "repo_type": "owner",
            "repo_name": "electron-note",
            "repo_description": "An offline desktop markdown note app based on Electron and React.",
            "repo_languages": "JavaScript",
            "repo_topics": ["electron", "react", "desktop-app"]
        },
        {
            "repo_type": "owner",
            "repo_name": "text2img",
            "repo_description": "Diffusion-based text to image generator using stable-diff.",
            "repo_languages": "Python",
            "repo_topics": ["diffusion", "text-to-image", "generative-ai"]
        }
    ]


    
    print("测试1：使用模拟数据分析领域")
    result = get_developer_domains_weighted("test-user", test_repositories,
                                            apply_tfidf=True,
                                            apply_softmax=True,
                                            softmax_temp=0.5)
    print("结果:")
    print(json.dumps(convert_numpy(result), indent=2, ensure_ascii=False))