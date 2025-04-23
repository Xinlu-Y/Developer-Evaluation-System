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

# 尝试导入config，如果失败则使用默认header
try:
    from config import headers
except ModuleNotFoundError:
    # 如果找不到config模块，使用默认的headers
    headers = {
        'User-Agent': 'Developer-Evaluation-System',
        'Accept': 'application/vnd.github.v3+json'
    }
    logging.warning("未找到config模块，使用默认headers")

# 配置日志格式
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
    # 如果模型未下载，提示错误但不自动下载
    logging.error("spaCy模型未找到。请先运行: python -m spacy download en_core_web_sm")
    # 创建一个空的NLP对象作为后备
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

# --- 仓库分析 ---
def analyze_repository(repo):
    name_kws = extract_keywords(repo.get('repo_name',''))
    desc_kws = extract_keywords(repo.get('repo_description',''))
    # 初始化三层级计分
    total_l1, total_l2, total_l3 = Counter(), Counter(), Counter()
    # 名称和描述
    for kws, signal in [(name_kws,'repo_name'), (desc_kws,'repo_description')]:
        l1,l2,l3 = map_keywords_to_domains(kws, signal)
        total_l1.update(l1)
        total_l2.update(l2)
        total_l3.update(l3)
    # topics
    for t in repo.get('topics',[]):
        m = match_domain_for_keyword(t)
        if m:
            lvl1, lvl2, lvl3, _ = m
            total_l1[lvl1] += SIGNAL_WEIGHTS['topics'] * LEVEL_WEIGHTS['topic']
            total_l2[lvl2] += SIGNAL_WEIGHTS['topics'] * LEVEL_WEIGHTS['topic']
            total_l3[lvl3] += SIGNAL_WEIGHTS['topics'] * LEVEL_WEIGHTS['topic']
    # language
    lang = repo.get('language','').lower()
    for lvl2 in LANGUAGE_TO_DOMAINS.get(lang,[]):
        lvl1 = L2_TO_L1.get(lvl2)
        w = SIGNAL_WEIGHTS['language'] * LEVEL_WEIGHTS['language']
        if lvl1:
            total_l1[lvl1] += w
        total_l2[lvl2] += w
    return total_l1, total_l2, total_l3

# --- 主分析函数 ---
def get_developer_domains(username, repos):
    """
    分析开发者的技术领域，返回分层结构:
    - level1: 一级领域及其得分
    - level2: 二级领域及其得分
    - level3: 层级3字段按二级领域分组的字典
    """
     # 只分析 owner 仓库
    repos = [r for r in repos if r.get('repo_type') == 'owner']
    total_l1, total_l2, total_l3 = Counter(), Counter(), Counter()

    # 如果没有仓库，返回空列表
    if not repos:
        return []

    # 1) 对每个仓库先归一化它自己的 l1、l2、l3 分
    for repo in repos:
        l1, l2, l3 = analyze_repository(repo)

        def local_normalize(c: Counter):
            if not c:
                return {}
            m = max(c.values())
            return {k: v / m for k, v in c.items()}

        norm_l1 = local_normalize(l1)
        norm_l2 = local_normalize(l2)
        norm_l3 = local_normalize(l3)

        # 累加回总计数器（每个仓库对每个领域的贡献都在 [0,1]）
        for k, v in norm_l1.items():
            total_l1[k] += v
        for k, v in norm_l2.items():
            total_l2[k] += v
        for k, v in norm_l3.items():
            total_l3[k] += v

    # 2) 把这三个总计数器归一化到 0–100
    def to_percent(c: Counter):
        if not c:
            return {}
        m = max(c.values())
        return {k: round(v / m * 100, 1) for k, v in c.items()}

    normalized_l1 = to_percent(total_l1)
    normalized_l2 = to_percent(total_l2)
    normalized_l3_flat = to_percent(total_l3)

    # 3) 将 level3 平铺结构按 level2 分组
    grouped_l3 = defaultdict(dict)
    for lvl3_name, score in normalized_l3_flat.items():
        lvl2_name = L3_TO_L2.get(lvl3_name.lower())
        if lvl2_name:
            grouped_l3[lvl2_name][lvl3_name] = score

    # 4) 构建树形结构
    hierarchy = []
    for lvl1_name, lvl1_score in normalized_l1.items():
        lvl1_node = {
            "name": lvl1_name,
            "score": lvl1_score,
            "children": []
        }
        # 把属于该一级领域的所有二级领域挂进去
        for lvl2_name, lvl2_score in normalized_l2.items():
            if L2_TO_L1.get(lvl2_name) == lvl1_name:
                lvl2_node = {
                    "name": lvl2_name,
                    "score": lvl2_score,
                    "children": []
                }
                # 把该二级领域下的三级细项挂进去
                for lvl3_name, lvl3_score in grouped_l3.get(lvl2_name, {}).items():
                    lvl2_node["children"].append({
                        "name": lvl3_name,
                        "score": lvl3_score
                    })
                lvl1_node["children"].append(lvl2_node)
        hierarchy.append(lvl1_node)

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
            "language": "JavaScript",
            "topics": ["vue", "vite", "admin-dashboard"]
        },
        {
            "repo_type": "owner",
            "repo_name": "flask_app_template",
            "repo_description": "A simple flask-based microservice API starter project",
            "language": "Python",
            "topics": ["flask", "rest", "microservice"]
        },
        {
            "repo_type": "owner",
            "repo_name": "llm-evaluator",
            "repo_description": "Using transformer-based LLMs for sentiment classification and QA tasks.",
            "language": "Python",
            "topics": ["llm", "transformers", "huggingface"]
        },
        {
            "repo_type": "owner",
            "repo_name": "open-vision",
            "repo_description": "Real-time object detection with yolov5 and OpenCV",
            "language": "Python",
            "topics": ["opencv", "object-detection", "yolo"]
        },
        {
            "repo_type": "owner",
            "repo_name": "qt_ui_generator",
            "repo_description": "Cross-platform GUI generator built with Qt6 and Python.",
            "language": "C++",
            "topics": ["qt", "cross-platform", "gui"]
        },
        {
            "repo_type": "owner",
            "repo_name": "data-analyse-toolkit",
            "repo_description": "EDA and visualization using pandas, seaborn, and matplotlib.",
            "language": "Python",
            "topics": ["eda", "visualization", "matplotlib"]
        },
        {
            "repo_type": "owner",
            "repo_name": "secure-web-auth",
            "repo_description": "OAuth2 + JWT authentication for single-page apps.",
            "language": "JavaScript",
            "topics": ["oauth", "jwt", "web-security"]
        },
        {
            "repo_type": "owner",
            "repo_name": "gameai-unity",
            "repo_description": "Exploring reinforcement learning with Unity ML-Agents toolkit",
            "language": "C#",
            "topics": ["unity", "reinforcement-learning", "ml-agents"]
        },
        {
            "repo_type": "owner",
            "repo_name": "electron-note",
            "repo_description": "An offline desktop markdown note app based on Electron and React.",
            "language": "JavaScript",
            "topics": ["electron", "react", "desktop-app"]
        },
        {
            "repo_type": "owner",
            "repo_name": "text2img",
            "repo_description": "Diffusion-based text to image generator using stable-diff.",
            "language": "Python",
            "topics": ["diffusion", "text-to-image", "generative-ai"]
        }
    ]

    
    print("测试1：使用模拟数据分析领域")
    result = get_developer_domains("test-user", test_repositories)
    print("结果:")
    print(json.dumps(convert_numpy(result), indent=2, ensure_ascii=False))
    # print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # # 测试异常情况 - 空仓库列表
    # print("\n测试2：空仓库列表")
    # result = get_developer_domains("test-user", [])
    # print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # # 测试异常情况 - 包含None的仓库
    # print("\n测试3：包含None的仓库列表")
    # corrupted_repos = test_repositories.copy()
    # corrupted_repos.insert(1, None)
    # result = get_developer_domains("test-user", corrupted_repos)
    # print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # # 测试异常情况 - 包含缺少关键字段的仓库
    # print("\n测试4：包含缺少关键字段的仓库")
    # incomplete_repos = test_repositories.copy()
    # incomplete_repos.append({"repo_type": "owner", "Star": 10})  # 没有repo_name
    # result = get_developer_domains("test-user", incomplete_repos)
    # print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # print("\n所有测试完成！") 