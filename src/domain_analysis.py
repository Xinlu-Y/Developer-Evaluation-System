import logging
import requests
import re
from collections import defaultdict, Counter
import spacy
import string
import json

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

# 扩展的技术领域映射表，增加了更多细分领域
DOMAIN_MAPPINGS = {
    # 前端技术
    'frontend': ['react', 'vue', 'angular', 'svelte', 'javascript', 'typescript', 'html', 'css', 'sass', 'less', 
                'webpack', 'vite', 'rollup', 'nextjs', 'nuxt', 'redux', 'vuex', 'tailwind', 'bootstrap', 'ui',
                'spa', 'pwa', 'webcomponents', 'dom', 'preact', 'ember', 'jquery', 'storybook', 'figma', 'sketch',
                'astro', 'solid', 'qwik', 'stimulus', 'alpinejs', 'lit', 'webassembly', 'wasm', 'responsive', 
                'animation', 'gsap', 'framer-motion', 'styled-components', 'emotion', 'css-in-js', 'css-modules',
                'accessibility', 'a11y', 'i18n', 'localization', 'seo', 'jamstack', 'remix', 'gatsby', 'vitejs',
                'ssr', 'isomorphic', 'microfrontend', 'web-vitals', 'pwa', 'service-worker', 'bun', 'deno', 'parcel'],
    
    # 后端技术
    'backend': ['node', 'express', 'django', 'flask', 'fastapi', 'spring', 'springboot', 'rails', 'laravel', 'php',
               'golang', 'java', 'kotlin', 'scala', 'graphql', 'rest', 'api', 'serverless', 'microservice',
               'nestjs', 'koa', 'ruby', 'aspnet', 'grpc', 'websocket', 'webrtc', 'oauth', 'jwt', 'authentication',
               'hapi', 'adonisjs', 'feathers', 'strapi', 'sails', 'moleculer', 'meteor', 'loopback', 'socketio',
               'sequelize', 'mongoose', 'typeorm', 'prisma', 'hibernate', 'jpa', 'akka', 'quarkus', 'micronaut',
               'ktor', 'actix', 'axum', 'rocket', 'echo', 'gin', 'fiber', 'symfony', 'cakephp', 'codeigniter',
               'vert.x', 'helidon', 'ratpack', 'dropwizard', 'bun', 'elysia', 'hono', 'middleware', 'validation'],
    
    # 移动开发
    'mobile': ['android', 'ios', 'swift', 'flutter', 'reactnative', 'xamarin', 'mobile', 'app', 'cordova',
              'ionic', 'kotlin', 'objective-c', 'dart', 'swiftui', 'jetpack', 'compose', 'watchos', 'tvos',
              'androidstudio', 'xcode', 'mobileui', 'realm', 'arkit', 'arcore', 'widgetkit', 'capacitor',
              'nativescript', 'phonegap', 'tauri', 'kotlin-multiplatform', 'kmm', 'kivy', 'maui', 'uikit',
              'androidx', 'material-design', 'material-you', 'room', 'lifecycle', 'navigation', 'workmanager',
              'codelabs', 'paging', 'viewmodel', 'livedata', 'coroutines', 'combine', 'rxswift', 'rxjava',
              'glance', 'appwidget', 'shortcuts', 'deeplink', 'push-notification', 'fcm', 'apns', 'in-app-purchase'],
    
    # 数据科学
    'data-science': ['datascience', 'machinelearning', 'ml', 'ai', 'deeplearning', 'tensorflow', 'pytorch', 'pandas',
                    'numpy', 'scipy', 'scikit-learn', 'jupyter', 'statistics', 'analytics', 'bigdata', 'dataanalysis',
                    'matplotlib', 'seaborn', 'plotly', 'regression', 'classification', 'clustering', 'forecasting',
                    'feature-engineering', 'etl', 'hypothesis', 'correlation', 'causation', 'data-mining',
                    'dask', 'spark', 'hadoop', 'xgboost', 'lightgbm', 'catboost', 'neural-network', 'cnn', 'rnn',
                    'lstm', 'gan', 'reinforcement-learning', 'unsupervised', 'supervised', 'bayesian', 'mcmc',
                    'dimensionality-reduction', 'pca', 'svd', 't-sne', 'umap', 'time-series', 'anomaly-detection',
                    'recommendation-system', 'nlp', 'feature-selection', 'grid-search', 'hyperparameter', 'cross-validation',
                    'ensemble', 'databricks', 'datarobot', 'knime', 'rapidminer', 'weka', 'orange', 'r-language'],
    
    # 大语言模型
    'llm': ['llm', 'nlp', 'gpt', 'bert', 'transformer', 'language-model', 'openai', 'langchain', 'chatbot',
           'prompt-engineering', 'semantic', 'embedding', 'text-generation', 'huggingface', 'rag',
           'token', 'tokenizer', 'fine-tuning', 'generative', 'llama', 'mistral', 'claude', 'attention',
           'vector-database', 'chroma', 'pinecone', 'milvus', 'document-qa', 'text-embedding',
           'gemini', 'cohere', 'falcon', 'anthropic', 'perplexity', 'bard', 'ollama', 'quantization', 'qlora',
           'few-shot', 'zero-shot', 'in-context', 'chain-of-thought', 'prompt-tuning', 'instruct', 'mixtral', 
           'multimodal', 'embedding', 'stable-diffusion', 'dall-e', 'midjourney', 'image-generation',
           'guardrails', 'inference', 'parameter', 'distillation', 'retrieval', 'hallucination', 'grounding',
           'jailbreak', 'dalle', 'gpt4-vision', 'text-to-image', 'text-to-speech', 'whisper', 'voice-cloning'],
    
    # 数据库
    'database': ['database', 'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'neo4j', 'cassandra',
                'dynamodb', 'orm', 'jdbc', 'nosql', 'firebase', 'supabase', 'indexing', 'transaction', 'shard',
                'replication', 'mariadb', 'sqlite', 'cockroachdb', 'couchdb', 'query', 'schema', 'migration',
                'prisma', 'sequelize', 'typeorm', 'entity', 'acid', 'integrity', 'normalization',
                'mssql', 'oracle', 'db2', 'clickhouse', 'timescaledb', 'influxdb', 'singlestore', 'planetscale',
                'snowflake', 'bigquery', 'redshift', 'scylladb', 'key-value', 'document', 'graph', 'time-series',
                'datomic', 'realm', 'arangodb', 'faunadb', 'dgraph', 'tigergraph', 'surrealdb', 'qdrant',
                'weaviate', 'redisvector', 'postgresql-vector', 'materialized-view', 'stored-procedure',
                'trigger', 'index', 'jsonb', 'foreign-key', 'constraint', 'join', 'aggregate', 'upsert'],
    
    # DevOps与云计算
    'devops': ['devops', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'cicd', 'jenkins', 'terraform', 'ansible',
              'monitoring', 'logging', 'cloud', 'serverless', 'infrastructure', 'github-actions', 'gitlab-ci',
              'circleci', 'travis', 'prometheus', 'grafana', 'elk', 'helm', 'istio', 'envoy', 'vault', 'consul',
              'nomad', 'ecs', 'fargate', 'lambda', 'iam', 'vpc', 's3', 'ec2', 'rds', 'heroku', 'vercel', 'netlify',
              'artifactory', 'argocd', 'fluentd', 'linkerd', 'datadog', 'newrelic', 'splunk', 'pagerduty',
              'cloudformation', 'pulumi', 'puppet', 'chef', 'saltstack', 'openshift', 'rancher', 'k3s', 'k9s',
              'kustomize', 'skaffold', 'podman', 'nerdctl', 'containerd', 'cri-o', 'buildah', 'kaniko', 'tekton',
              'crossplane', 'gitops', 'devopssec', 'sre', 'chaos-engineering', 'observability', 'tracing', 'jaeger',
              'opentelemetry', 'container-registry', 'artifact-hub', 'digitalocean', 'linode', 'lightsail'],
    
    # 游戏开发
    'gamedev': ['game', 'gamedev', 'unity', 'unreal', 'threejs', 'webgl', 'godot', 'gamification', 'simulator',
               'graphics', 'ar', 'vr', 'xr', 'directx', 'opengl', 'vulkan', 'metal', 'shader', 'physics',
               'procedural', 'pathfinding', 'animation', 'particles', 'rendering', 'collision', 'sprite', 'texture',
               'mesh', 'rigging', 'blender', 'maya', 'game-engine', 'level-design', 'game-mechanics',
               'phaser', 'pixi', 'babylon', 'playcanvas', 'construct', 'rpgmaker', 'gamemaker', 'gdevelop',
               'lumberyard', 'cryengine', 'fmod', 'wwise', 'havok', 'physx', 'box2d', 'chipmunk', 'gameprogramming',
               'gameplay', 'locomotion', 'inventory', 'quest', 'dialogue', 'behavior-tree', 'state-machine',
               'inverse-kinematics', 'character-controller', 'navmesh', 'occlusion-culling', 'baking',
               'light-mapping', 'post-processing', 'vfx', 'decal', 'reflection-probe', 'lightmass', 'luascript'],
    
    # 安全
    'security': ['security', 'encryption', 'cybersecurity', 'authentication', 'authorization', 'jwt', 'oauth',
                'cryptography', 'privacy', 'pentesting', 'vulnerability', 'firewall', 'ssl', 'tls', 'cve',
                'threat-modeling', 'zero-trust', 'appsec', 'ctf', 'exploit', 'malware', 'ransomware', 'phishing',
                'social-engineering', 'incident-response', 'forensics', 'intrusion-detection', 'compliance',
                'burp-suite', 'metasploit', 'wireshark', 'kali', 'owasp', 'csrf', 'xss', 'sqli', 'ssrf', 'rce',
                'dos', 'mitm', 'spoofing', 'backdoor', 'reverse-engineering', 'binary-analysis', 'fuzzing',
                'threat-intelligence', 'darkweb', 'tor', 'vpn', 'privacy', 'gdpr', 'hipaa', 'sox', 'ccpa',
                'pci-dss', 'iso27001', 'nist', 'hashing', 'salting', 'hmac', 'openssl', 'pgp', 'gpg', 'keylogger',
                'rootkit', 'pam', 'dmarc', 'spf', 'dkim', 'security-headers', 'csp', 'waf', 'botnet', 'idp'],
    
    # 区块链
    'blockchain': ['blockchain', 'ethereum', 'solidity', 'web3', 'cryptocurrency', 'bitcoin', 'nft', 'defi',
                  'smart-contract', 'wallet', 'token', 'consensus', 'mining', 'node', 'ledger', 'dao', 'dapp',
                  'metamask', 'uniswap', 'aave', 'compound', 'chainlink', 'polkadot', 'substrate', 'staking',
                  'yield-farming', 'erc20', 'erc721', 'tokenomics', 'hardhat', 'truffle', 'ganache',
                  'polygon', 'solana', 'rust', 'anchor', 'avalanche', 'cosmos', 'tendermint', 'binance', 'bnb',
                  'arbitrum', 'optimism', 'rollup', 'zk-proof', 'zero-knowledge', 'snarks', 'starks', 'cardano',
                  'haskell', 'plutus', 'tezos', 'ocaml', 'algorand', 'near', 'flow', 'cadence', 'filecoin',
                  'ipfs', 'arweave', 'stablecoin', 'dai', 'usdc', 'tether', 'usdt', 'amm', 'dex', 'liquidity',
                  'yield', 'governance', 'multisig', 'merkle', 'ethers', 'web3js', 'wagmi', 'viem', 'thirdweb'],
                  
    # 系统编程
    'systems': ['rust', 'c', 'cpp', 'c++', 'assembly', 'kernel', 'rtos', 'embedded', 'firmware', 'driver',
                'memory-management', 'concurrency', 'parallelism', 'mutex', 'semaphore', 'thread', 'process',
                'ipc', 'compiler', 'linker', 'allocator', 'garbage-collection', 'llvm', 'jit', 'bytecode',
                'filesystem', 'network-programming', 'socket', 'protocol', 'io', 'mmap', 'syscall',
                'operating-system', 'linux', 'unix', 'windows', 'macos', 'posix', 'scheduler', 'interrupt',
                'virtualization', 'hypervisor', 'qemu', 'vbox', 'kvm', 'xen', 'esxi', 'hyper-v', 'container',
                'namespace', 'cgroup', 'capability', 'seccomp', 'ebpf', 'xdp', 'microkernel', 'monolithic',
                'zig', 'asm', 'simd', 'avx', 'sse', 'neon', 'intrinsic', 'inline-assembly', 'device-driver',
                'bpf', 'dtrace', 'systemtap', 'perf', 'ftrace', 'profiling', 'benchmark', 'memory-leak',
                'race-condition', 'deadlock', 'starvation', 'atomic', 'volatile', 'barrier', 'spinlock'],
                
    # 计算机图形学
    'graphics': ['rendering', 'shader', 'opengl', 'vulkan', 'directx', 'metal', 'webgl', 'raytracing',
                'rasterization', 'shadow-mapping', 'pbr', 'brdf', 'tessellation', 'geometry', 'mesh',
                'vertex', 'fragment', 'compute', 'texture', 'normal-mapping', 'global-illumination',
                'ambient-occlusion', 'anti-aliasing', 'deferred-rendering', 'csg', 'procedural-generation',
                'hlsl', 'glsl', 'path-tracing', 'radiosity', 'irradiance', 'cubemap', 'environment-map',
                'subsurface-scattering', 'volumetric', 'lightfield', 'culling', 'frustum', 'occlusion',
                'level-of-detail', 'mipmapping', 'texture-compression', 'astc', 'bc7', 'etc2', 'pvrtc',
                'bsdf', 'bssrdf', 'gi', 'dx12', 'dx11', 'rtx', 'vk', 'wgpu', 'postprocessing', 'fxaa',
                'ssao', 'ssr', 'parallax', 'lod', 'voxel', 'sdf', 'displacement', 'tesselation', 'skinning',
                'nurbs', 'spline', 'parametric', 'marching-cubes', 'gpu-instancing', 'compute-shader'],
    
    # 计算机视觉
    'computer-vision': ['opencv', 'image-processing', 'object-detection', 'segmentation', 'feature-extraction',
                       'edge-detection', 'sift', 'orb', 'yolo', 'rcnn', 'cnn', 'depth-estimation', 'slam',
                       'optical-flow', 'tracking', 'face-recognition', 'pose-estimation', 'augmented-reality',
                       'stereo-vision', 'homography', 'calibration', 'photogrammetry', 'image-recognition',
                       'mediapipe', 'tensorflow-vision', 'detectron', 'albumentations', 'mmdetection',
                       'mmpose', 'mmsegmentation', 'mim', 'kornia', 'onnx-vision', 'mask-rcnn', 'faster-rcnn',
                       'retinanet', 'ssd', 'efficientdet', 'vit', 'detr', 'sam', 'segment-anything',
                       'monocular', 'depth-map', 'point-cloud', 'bundle-adjustment', 'structure-from-motion',
                       'multi-view', 'keypoint', 'descriptor', 'hog', 'contour', 'watershed', 'thresholding',
                       'filtering', 'convolution', 'morphological', 'hough', 'ransac', 'epipolar', 'motion'],
                       
    # # 教育和学习
    # 'education': ['course', 'tutorial', 'learning', 'teaching', 'educational', 'assignment', 'homework', 'lecture',
    #              'study', 'curriculum', 'syllabus', 'bootcamp', 'training', 'workshop', 'textbook', 'notes',
    #              'certification', 'mooc', 'quiz', 'exercise', 'practice', 'problem-set', 'lab', 'exam',
    #              'elearning', 'lms', 'moodle', 'canvas', 'blackboard', 'brightspace', 'edx', 'coursera',
    #              'udemy', 'khan-academy', 'udacity', 'pluralsight', 'linkedin-learning', 'skillshare', 'teacher',
    #              'student', 'professor', 'instructor', 'classroom', 'lesson', 'pedagogy', 'rubric', 'assessment',
    #              'evaluation', 'feedback', 'grade', 'peer-review', 'project-based', 'inquiry-based',
    #              'flipped-classroom', 'micro-learning', 'spaced-repetition', 'gamification', 'vr-learning',
    #              'stem', 'steam', 'computer-science', 'programming-course', 'coding-bootcamp', 'cs50'],
                 
    # 人工智能
    'ai': ['artificial-intelligence', 'machine-learning', 'neural-network', 'deep-learning', 'reinforcement-learning',
         'supervised', 'unsupervised', 'semi-supervised', 'generative', 'discriminative', 'bayesian', 'decision-tree',
         'random-forest', 'svm', 'knn', 'naive-bayes', 'clustering', 'dimensionality-reduction', 'pca', 'tda',
         'transfer-learning', 'meta-learning', 'few-shot', 'zero-shot', 'active-learning', 'federated-learning',
         'swarm-intelligence', 'evolutionary-algorithm', 'genetic-algorithm', 'gan', 'vae', 'diffusion-model',
         'autoencoder', 'transformer', 'attention', 'self-supervised', 'contrastive-learning', 'anomaly-detection',
         'recommendation-system', 'knowledge-graph', 'expert-system', 'autonomous', 'multi-agent', 'robotics',
         'computer-vision', 'natural-language-processing', 'speech-recognition', 'text-to-speech', 'agi'],
                 
    # 机器人和物联网
    'robotics-iot': ['robotics', 'iot', 'robot', 'autonomous', 'sensor', 'actuator', 'servo', 'motor', 'controller',
                    'arduino', 'raspberry-pi', 'esp32', 'esp8266', 'stm32', 'microcontroller', 'mcu', 'ros',
                    'ros2', 'gazebo', 'simulation', 'digital-twin', 'mqtt', 'coap', 'lorawan', 'zigbee', 'zwave',
                    'bluetooth', 'ble', 'wifi', 'thread', 'matter', 'kinematics', 'path-planning', 'localization',
                    'slam', 'navigation', 'control-system', 'pid', 'feedback', 'drone', 'uav', 'quadcopter',
                    'autopilot', 'computer-vision', 'depth-sensor', 'lidar', 'radar', 'ultrasonic', 'gyroscope',
                    'accelerometer', 'magnetometer', 'imu', 'home-automation', 'smart-home', 'smart-city',
                    'industry-4.0', 'plc', 'scada', 'modbus', 'canbus', 'ethernet-ip', 'opc-ua', 'protocol'],
                    
    # 生物信息学
    'bioinformatics': ['bioinformatics', 'genomics', 'proteomics', 'sequencing', 'dna', 'rna', 'gene', 'genome',
                      'protein', 'biology', 'molecular', 'cell', 'phylogenetics', 'evolution', 'biostatistics',
                      'systems-biology', 'metabolomics', 'transcriptomics', 'epigenetics', 'homology', 'alignment',
                      'blast', 'clustal', 'hmm', 'msa', 'phylogeny', 'motif', 'pathway', 'ontology', 'go',
                      'kegg', 'reactome', 'ensembl', 'ucsc', 'ncbi', 'genbank', 'sra', 'fastq', 'fasta',
                      'sam', 'bam', 'vcf', 'variant', 'snp', 'indel', 'gwas', 'qtl', 'eqtl', 'crispr',
                      'metagenomics', 'microbiome', 'taxonomy', 'nextgen', 'ngs', 'illumina', 'pacbio', 'nanopore',
                      'r-bioconductor', 'biopython', 'biojs', 'igv', 'jalview', 'pymol', 'cytoscape'],
                      
    # 网络和通信
    'networking': ['networking', 'network', 'protocol', 'tcp', 'ip', 'udp', 'http', 'https', 'dns', 'dhcp',
                  'vpn', 'router', 'switch', 'gateway', 'firewall', 'ipsec', 'ssl', 'tls', 'ssh', 'ftp',
                  'smtp', 'pop3', 'imap', 'websocket', 'webrtc', 'mqtt', 'amqp', 'quic', 'grpc', 'rpc',
                  'rest', 'graphql', 'soap', 'osi', 'ipv4', 'ipv6', 'subnet', 'vlan', 'bgp', 'ospf',
                  'mpls', 'sdn', 'nfv', 'proxy', 'load-balancer', 'cdn', 'ddos', 'latency', 'bandwidth',
                  'throughput', 'jitter', 'packet', 'frame', 'encapsulation', 'wireshark', 'tcpdump',
                  'netstat', 'ping', 'traceroute', 'nmap', 'wifi', 'bluetooth', 'zigbee', '5g', 'lte'],
                  
    # 音频工程
    'audio': ['audio', 'sound', 'music', 'dsp', 'signal-processing', 'acoustics', 'synthesis', 'sampling',
             'wav', 'mp3', 'aac', 'flac', 'codec', 'compression', 'pcm', 'spectrum', 'frequency', 'amplitude',
             'waveform', 'envelope', 'reverb', 'delay', 'filter', 'eq', 'compression', 'limiter', 'gate',
             'noise-reduction', 'audio-plugin', 'vst', 'au', 'lv2', 'midi', 'sequencer', 'daw', 'ableton',
             'protools', 'logic', 'fl-studio', 'cubase', 'reaper', 'supercollider', 'puredata', 'max-msp',
             'csound', 'chuck', 'juce', 'fmod', 'wwise', 'audacity', 'tts', 'stt', 'voice', 'speech',
             'synthesis', 'vocoder', 'pitch-detection', 'onset-detection', 'fourier', 'fft', 'stft', 'wavelets']
}

# 反向映射（关键词到领域）
KEYWORD_TO_DOMAIN = {}
for domain, keywords in DOMAIN_MAPPINGS.items():
    for keyword in keywords:
        KEYWORD_TO_DOMAIN[keyword] = domain

# 技术相关的停用词
TECH_STOP_WORDS = set(['app', 'application', 'system', 'tool', 'toolkit', 'framework', 'library', 'platform', 
                      'project', 'code', 'demo', 'example', 'test', 'sample', 'implementation', 'introduction',
                      'solution', 'development', 'template', 'boilerplate', 'starter', 'package', 'module'])

# 扩展的技术知识图谱 - 增加了更多细分技术领域、语言和框架的关联
TECH_KNOWLEDGE_GRAPH = {
    # 前端技术
    'react': ['frontend', 'javascript', 'ui', 'web', 'component', 'jsx', 'hooks', 'redux', 'state-management'],
    'vue': ['frontend', 'javascript', 'ui', 'web', 'component', 'template', 'composition-api', 'vuex'],
    'angular': ['frontend', 'typescript', 'ui', 'web', 'component', 'rxjs', 'dependency-injection', 'template'],
    'javascript': ['frontend', 'web', 'scripting', 'node', 'browser', 'es6', 'event-driven', 'asynchronous'],
    'typescript': ['frontend', 'javascript', 'typed', 'web', 'interface', 'generics', 'enums', 'decorators'],
    'webpack': ['frontend', 'bundler', 'javascript', 'module', 'optimization', 'asset-management'],
    'nextjs': ['frontend', 'react', 'ssr', 'web', 'jamstack', 'static-site', 'file-based-routing'],
    'tailwind': ['frontend', 'css', 'ui', 'utility-first', 'responsive', 'customization'],
    'svelte': ['frontend', 'javascript', 'ui', 'web', 'component', 'reactivity', 'compiler'],
    'astro': ['frontend', 'web', 'static-site', 'islands', 'jsx', 'partial-hydration', 'multi-framework'],
    'qwik': ['frontend', 'javascript', 'resumable', 'ui', 'builder.io', 'lazy-loading', 'performance'],
    'remix': ['frontend', 'react', 'ssr', 'web', 'nested-routing', 'data-loading', 'mutation'],
    
    # 后端技术
    'django': ['backend', 'python', 'web', 'server', 'orm', 'template', 'admin', 'authentication'],
    'flask': ['backend', 'python', 'web', 'microframework', 'routing', 'wsgi', 'jinja', 'blueprint'],
    'fastapi': ['backend', 'python', 'api', 'async', 'pydantic', 'swagger', 'dependency-injection', 'performance'],
    'spring': ['backend', 'java', 'enterprise', 'server', 'dependency-injection', 'aop', 'orm', 'transaction'],
    'express': ['backend', 'node', 'javascript', 'web', 'middleware', 'routing', 'rest'],
    'graphql': ['backend', 'api', 'query', 'schema', 'resolver', 'subscription', 'federation'],
    'rest': ['backend', 'api', 'http', 'resource', 'endpoint', 'stateless', 'representation'],
    'microservice': ['backend', 'architecture', 'scalable', 'distributed', 'service-oriented', 'containerization'],
    'nestjs': ['backend', 'typescript', 'node', 'framework', 'decorators', 'dependency-injection', 'modular'],
    'quarkus': ['backend', 'java', 'kubernetes-native', 'graalvm', 'fast-startup', 'low-memory', 'microservice'],
    'axum': ['backend', 'rust', 'async', 'tower', 'web', 'routing', 'middleware', 'handler'],
    'gin': ['backend', 'golang', 'http', 'router', 'middleware', 'web', 'api', 'performance'],
    
    # 移动开发
    'android': ['mobile', 'java', 'kotlin', 'app', 'activity', 'fragment', 'intent', 'jetpack'],
    'ios': ['mobile', 'swift', 'objective-c', 'app', 'uikit', 'viewcontroller', 'cocoapods', 'swiftui'],
    'flutter': ['mobile', 'dart', 'cross-platform', 'ui', 'widget', 'state-management', 'material-design'],
    'reactnative': ['mobile', 'javascript', 'react', 'cross-platform', 'native-modules', 'bridge'],
    'jetpack-compose': ['mobile', 'android', 'kotlin', 'declarative', 'ui', 'material-design', 'composable'],
    'swiftui': ['mobile', 'ios', 'swift', 'declarative', 'ui', 'combine', 'preview', 'property-wrapper'],
    'kotlin-multiplatform': ['mobile', 'kotlin', 'cross-platform', 'shared-code', 'native', 'jvm', 'js'],
    'capacitor': ['mobile', 'web', 'hybrid', 'ionic', 'plugin', 'native-api', 'progressive-web-app'],
    
    # 数据科学
    'tensorflow': ['data-science', 'machine-learning', 'python', 'neural-networks', 'gpu', 'model-training'],
    'pytorch': ['data-science', 'machine-learning', 'python', 'neural-networks', 'autograd', 'dynamic-graph'],
    'pandas': ['data-science', 'python', 'data-analysis', 'tabular', 'dataframe', 'series', 'indexing'],
    'numpy': ['data-science', 'python', 'numerical', 'computing', 'array', 'vectorization', 'linear-algebra'],
    'jupyter': ['data-science', 'python', 'notebook', 'interactive', 'visualization', 'reproducibility'],
    'scikit-learn': ['data-science', 'machine-learning', 'python', 'classification', 'regression', 'clustering'],
    'xgboost': ['data-science', 'machine-learning', 'gradient-boosting', 'decision-tree', 'ensemble'],
    'dask': ['data-science', 'python', 'parallel', 'distributed', 'dataframe', 'array', 'big-data'],
    
    # LLM相关
    'transformer': ['llm', 'nlp', 'ai', 'architecture', 'attention', 'encoder-decoder', 'self-attention'],
    'bert': ['llm', 'nlp', 'embedding', 'google', 'pre-training', 'fine-tuning', 'bidirectional'],
    'gpt': ['llm', 'generative', 'openai', 'text-generation', 'autoregressive', 'decoder-only', 'transformer'],
    'langchain': ['llm', 'framework', 'agents', 'rag', 'prompt-engineering', 'chain-of-thought', 'integration'],
    'huggingface': ['llm', 'platform', 'models', 'transformers', 'datasets', 'tokenizers', 'pipeline'],
    'llama': ['llm', 'meta', 'open-source', 'large-language-model', 'inference', 'fine-tuning'],
    'rag': ['llm', 'retrieval', 'augmented', 'generation', 'document', 'embedding', 'context'],
    'mistral': ['llm', 'open-source', 'mixture-of-experts', 'instruction-tuned', 'french', 'performance'],
    
    # 数据库
    'mysql': ['database', 'sql', 'relational', 'acid', 'query', 'transaction', 'schema'],
    'postgresql': ['database', 'sql', 'relational', 'advanced', 'jsonb', 'gis', 'extensions'],
    'mongodb': ['database', 'nosql', 'document', 'bson', 'collection', 'aggregate', 'index'],
    'redis': ['database', 'nosql', 'in-memory', 'key-value', 'caching', 'pub-sub', 'data-structures'],
    'elasticsearch': ['database', 'search', 'indexing', 'analytics', 'full-text', 'distributed', 'lucene'],
    'neo4j': ['database', 'graph', 'cypher', 'nodes', 'relationships', 'property-graph', 'traversal'],
    'cassandra': ['database', 'nosql', 'distributed', 'column-family', 'wide-column', 'scalability'],
    'clickhouse': ['database', 'olap', 'column-oriented', 'analytics', 'data-warehouse', 'sql', 'performance'],
    
    # DevOps
    'docker': ['devops', 'container', 'virtualization', 'image', 'registry', 'isolation', 'dockerfile'],
    'kubernetes': ['devops', 'orchestration', 'container', 'pod', 'service', 'deployment', 'autoscaling'],
    'aws': ['devops', 'cloud', 'amazon', 'services', 'ec2', 's3', 'lambda', 'iam'],
    'azure': ['devops', 'cloud', 'microsoft', 'services', 'vm', 'blob', 'functions', 'active-directory'],
    'github-actions': ['devops', 'cicd', 'automation', 'workflow', 'pipeline', 'integration', 'deployment'],
    'terraform': ['devops', 'infrastructure-as-code', 'provisioning', 'cloud', 'resource', 'state', 'module'],
    'ansible': ['devops', 'configuration-management', 'automation', 'playbook', 'role', 'inventory', 'idempotent'],
    'prometheus': ['devops', 'monitoring', 'metrics', 'alerting', 'time-series', 'scraping', 'visualization'],
    'argocd': ['devops', 'gitops', 'kubernetes', 'continuous-delivery', 'application', 'sync', 'declarative'],
    'istio': ['devops', 'service-mesh', 'traffic-management', 'security', 'observability', 'kubernetes'],
    
    # 游戏开发
    'unity': ['gamedev', 'engine', 'c#', '3d', 'prefab', 'scene', 'component', 'physics'],
    'unreal': ['gamedev', 'engine', 'c++', '3d', 'blueprint', 'actor', 'component', 'material'],
    'godot': ['gamedev', 'engine', 'open-source', 'gdscript', 'node', 'scene', '2d', '3d'],
    'webgl': ['gamedev', 'graphics', 'javascript', 'web', '3d', 'shader', 'canvas', 'rendering'],
    'threejs': ['gamedev', 'graphics', 'javascript', 'web', '3d', 'scene', 'mesh', 'material'],
    'phaser': ['gamedev', 'javascript', 'html5', '2d', 'canvas', 'webgl', 'sprite', 'physics'],
    'gamemaker': ['gamedev', 'engine', '2d', 'gml', 'drag-and-drop', 'sprite', 'room', 'object'],
    'babylon': ['gamedev', 'javascript', '3d', 'webgl', 'pbr', 'physics', 'animation', 'scene'],
    
    # 安全
    'encryption': ['security', 'cryptography', 'privacy', 'cipher', 'key', 'algorithm', 'confidentiality'],
    'jwt': ['security', 'authentication', 'token', 'claims', 'signature', 'header', 'payload'],
    'oauth': ['security', 'authentication', 'authorization', 'flow', 'scope', 'token', 'identity'],
    'pentesting': ['security', 'vulnerability', 'exploit', 'hack', 'assessment', 'penetration', 'ethical'],
    'firewall': ['security', 'network', 'filtering', 'rules', 'packet', 'inspection', 'protection'],
    'owasp': ['security', 'web', 'vulnerability', 'top-ten', 'best-practices', 'appsec', 'community'],
    'threat-modeling': ['security', 'risk', 'design', 'analysis', 'mitigation', 'attack-vector', 'stride'],
    
    # 区块链
    'ethereum': ['blockchain', 'cryptocurrency', 'smart-contract', 'web3', 'solidity', 'evm', 'gas'],
    'solidity': ['blockchain', 'language', 'ethereum', 'smart-contract', 'evm', 'bytecode', 'function'],
    'web3': ['blockchain', 'decentralized', 'dapps', 'ethereum', 'wallet', 'transaction', 'interaction'],
    'bitcoin': ['blockchain', 'cryptocurrency', 'satoshi', 'mining', 'pow', 'btc', 'wallet'],
    'nft': ['blockchain', 'token', 'non-fungible', 'collectible', 'digital-art', 'ownership', 'metadata'],
    'defi': ['blockchain', 'finance', 'decentralized', 'lending', 'borrowing', 'yield', 'swap'],
    'solana': ['blockchain', 'cryptocurrency', 'rust', 'proof-of-history', 'spl', 'fast', 'scalable'],
    'polygon': ['blockchain', 'ethereum', 'layer2', 'scaling', 'pos', 'matic', 'sidechain'],
    
    # 系统编程
    'rust': ['systems', 'language', 'memory-safety', 'concurrency', 'ownership', 'borrowing', 'trait', 'generic'],
    'c++': ['systems', 'language', 'performance', 'memory-management', 'class', 'template', 'stl', 'pointer'],
    'c': ['systems', 'language', 'low-level', 'performance', 'pointer', 'struct', 'memory', 'preprocessor'],
    'kernel': ['systems', 'operating-system', 'driver', 'module', 'scheduler', 'memory', 'resource'],
    'embedded': ['systems', 'hardware', 'firmware', 'microcontroller', 'real-time', 'bare-metal', 'iot'],
    'concurrency': ['systems', 'parallel', 'threading', 'async', 'synchronization', 'mutex', 'atomics'],
    'compiler': ['systems', 'language', 'optimization', 'parsing', 'code-generation', 'llvm', 'frontend'],
    'zig': ['systems', 'language', 'memory-safety', 'compile-time', 'error-handling', 'no-hidden-control-flow'],
    
    # 计算机图形学
    'opengl': ['graphics', 'api', 'rendering', 'shader', '3d', 'pipeline', 'buffer', 'texture'],
    'vulkan': ['graphics', 'api', 'rendering', 'shader', 'low-level', 'explicit', 'synchronization'],
    'shader': ['graphics', 'program', 'rendering', 'gpu', 'vertex', 'fragment', 'compute', 'lighting'],
    'raytracing': ['graphics', 'rendering', 'reflection', 'refraction', 'global-illumination', 'pathtrace'],
    'shadow-mapping': ['graphics', 'technique', 'lighting', 'shadows', 'depth-map', 'rendering'],
    'pbr': ['graphics', 'physically-based', 'rendering', 'material', 'brdf', 'metalness', 'roughness'],
    'directx': ['graphics', 'microsoft', 'api', 'd3d', 'shader', 'gaming', 'windows', 'hlsl'],
    'webgpu': ['graphics', 'api', 'web', 'compute', 'modern', 'cross-platform', 'dawn', 'wgsl'],
    
    # 计算机视觉
    'opencv': ['computer-vision', 'library', 'image-processing', 'feature-detection', 'filtering', 'calibration'],
    'segmentation': ['computer-vision', 'technique', 'pixel-classification', 'object-detection', 'mask'],
    'yolo': ['computer-vision', 'algorithm', 'object-detection', 'real-time', 'bounding-box', 'neural-network'],
    'mediapipe': ['computer-vision', 'framework', 'google', 'pose', 'face', 'hand', 'cross-platform'],
    'slam': ['computer-vision', 'robotics', 'mapping', 'localization', 'odometry', '3d-reconstruction'],
    'depth-estimation': ['computer-vision', '3d', 'stereo', 'monocular', 'disparity', 'depth-map'],
    'face-recognition': ['computer-vision', 'biometrics', 'detection', 'landmark', 'identification', 'verification'],
    'optical-flow': ['computer-vision', 'motion', 'tracking', 'estimation', 'vector-field', 'displacement'],
    
    # # 教育和学习
    # 'course': ['education', 'learning', 'curriculum', 'lecture', 'assignment', 'grade', 'instructor'],
    # 'assignment': ['education', 'task', 'homework', 'project', 'learning', 'submission', 'deadline'],
    # 'tutorial': ['education', 'guide', 'learning', 'step-by-step', 'instruction', 'example', 'practice'],
    # 'mooc': ['education', 'online', 'course', 'massive', 'open', 'video', 'certificate'],
    # 'lms': ['education', 'learning-management', 'system', 'platform', 'course', 'assessment', 'grades'],
    # 'bootcamp': ['education', 'intensive', 'training', 'practical', 'career', 'skills', 'industry'],
    # 'workshop': ['education', 'practical', 'hands-on', 'session', 'interactive', 'group', 'facilitator'],
    # 'cs50': ['education', 'harvard', 'programming', 'computer-science', 'introduction', 'david-malan'],
    
    # 人工智能
    'neural-network': ['ai', 'deep-learning', 'neuron', 'layer', 'activation', 'weights', 'backpropagation'],
    'reinforcement-learning': ['ai', 'agent', 'environment', 'reward', 'policy', 'q-learning', 'markov'],
    'generative-model': ['ai', 'gan', 'vae', 'diffusion', 'creation', 'synthetic', 'generation'],
    'knowledge-graph': ['ai', 'semantic', 'ontology', 'entity', 'relation', 'triple', 'reasoning'],
    'autonomous': ['ai', 'self-driving', 'agent', 'decision', 'planning', 'sensing', 'control'],
    'diffusion-model': ['ai', 'generative', 'noise', 'denoising', 'stable-diffusion', 'image-generation'],
    'multi-agent': ['ai', 'system', 'cooperation', 'communication', 'swarm', 'coordination', 'emergent'],
    'transformer': ['ai', 'attention', 'self-attention', 'encoder', 'decoder', 'nlp', 'sequence'],
    
    # 机器人和物联网
    'robotics': ['robotics-iot', 'robot', 'mechatronics', 'control', 'automation', 'kinematics', 'actuator'],
    'ros': ['robotics-iot', 'robot-operating-system', 'middleware', 'node', 'topic', 'service', 'message'],
    'arduino': ['robotics-iot', 'microcontroller', 'prototyping', 'electronics', 'sensor', 'sketch', 'board'],
    'raspberry-pi': ['robotics-iot', 'single-board', 'computer', 'gpio', 'linux', 'python', 'embedded'],
    'esp32': ['robotics-iot', 'microcontroller', 'wifi', 'bluetooth', 'iot', 'low-power', 'espressif'],
    'mqtt': ['robotics-iot', 'protocol', 'messaging', 'publish-subscribe', 'lightweight', 'iot', 'broker'],
    'iot': ['robotics-iot', 'internet-of-things', 'connected', 'device', 'sensor', 'network', 'data'],
    'drone': ['robotics-iot', 'uav', 'quadcopter', 'flight-controller', 'aerial', 'navigation', 'autonomous'],
    
    # 生物信息学
    'bioinformatics': ['bioinformatics', 'biology', 'genomics', 'sequence', 'analysis', 'alignment', 'annotation'],
    'genomics': ['bioinformatics', 'genome', 'dna', 'sequencing', 'analysis', 'variation', 'assembly'],
    'proteomics': ['bioinformatics', 'protein', 'structure', 'function', 'mass-spectrometry', 'analysis'],
    'sequencing': ['bioinformatics', 'dna', 'rna', 'ngs', 'illumina', 'pacbio', 'nanopore'],
    'phylogenetics': ['bioinformatics', 'evolution', 'tree', 'taxonomy', 'species', 'clade', 'divergence'],
    'blast': ['bioinformatics', 'sequence-alignment', 'search', 'database', 'homology', 'similarity'],
    'metagenomics': ['bioinformatics', 'microbiome', 'community', 'ecology', 'environmental', 'diversity'],
    'crispr': ['bioinformatics', 'gene-editing', 'cas9', 'genome-engineering', 'target', 'guide-rna'],
    
    # 网络和通信
    'networking': ['networking', 'protocol', 'communication', 'packet', 'router', 'switch', 'lan'],
    'tcp-ip': ['networking', 'protocol', 'transmission-control', 'internet', 'packet', 'connection', 'socket'],
    'http': ['networking', 'protocol', 'web', 'request', 'response', 'header', 'status-code'],
    'dns': ['networking', 'domain-name-system', 'lookup', 'nameserver', 'resolution', 'record', 'zone'],
    'vpn': ['networking', 'virtual-private-network', 'tunnel', 'encryption', 'remote-access', 'security'],
    'sdn': ['networking', 'software-defined', 'controller', 'openflow', 'programmable', 'virtualization'],
    'firewall': ['networking', 'security', 'filter', 'policy', 'traffic', 'protection', 'rule'],
    '5g': ['networking', 'cellular', 'mobile', 'high-speed', 'low-latency', 'network-slicing', 'mmwave'],
    
    # 音频工程
    'audio': ['audio', 'sound', 'signal', 'waveform', 'frequency', 'amplitude', 'processing'],
    'dsp': ['audio', 'digital-signal-processing', 'filter', 'transform', 'algorithm', 'analysis', 'synthesis'],
    'synthesis': ['audio', 'sound-generation', 'oscillator', 'modulation', 'waveform', 'additive', 'subtractive'],
    'midi': ['audio', 'musical-instrument-digital-interface', 'protocol', 'note', 'controller', 'sequencer'],
    'daw': ['audio', 'digital-audio-workstation', 'recording', 'editing', 'mixing', 'production', 'software'],
    'plugin': ['audio', 'vst', 'au', 'lv2', 'effect', 'instrument', 'processor', 'extension'],
    'fft': ['audio', 'fast-fourier-transform', 'frequency-domain', 'spectrum', 'analysis', 'algorithm'],
    'reverb': ['audio', 'reverberation', 'effect', 'space', 'decay', 'diffusion', 'reflection']
}

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

# 项目类型识别模式
PROJECT_TYPE_PATTERNS = {
    'course': [r'cs\d+', r'course', r'class', r'assignment', r'homework', r'lab\d+', r'exercise', r'lecture'],
    'tutorial': [r'tutorial', r'guide', r'learn', r'begin', r'start', r'intro to', r'introduction to'],
    'demo': [r'demo', r'example', r'sample', r'showcase', r'boilerplate', r'starter', r'template'],
    'library': [r'library', r'framework', r'sdk', r'toolkit', r'package', r'module', r'wrapper', r'client'],
    'tool': [r'tool', r'utility', r'cli', r'plugin', r'extension', r'addon', r'script', r'automation'],
    'app': [r'app', r'application', r'platform', r'service', r'system', r'website', r'webapp', r'mobile app'],
    'game': [r'game', r'gameplay', r'arcade', r'puzzle', r'simulator', r'engine', r'interactive', r'vr ', r'ar '],
    'research': [r'research', r'paper', r'thesis', r'dissertation', r'study', r'experiment', r'analysis']
}

def enhance_with_knowledge_graph(tech_keywords):
    """使用知识图谱扩展技术关键词"""
    logger.debug(f"知识图谱扩展前的关键词: {tech_keywords}")
    
    expanded_keywords = set(tech_keywords)
    expanded_terms = {}  # 用于记录每个关键词扩展出的词汇
    
    for keyword in tech_keywords:
        # 查找知识图谱中的相关词
        related_terms = TECH_KNOWLEDGE_GRAPH.get(keyword, [])
        if related_terms:
            expanded_terms[keyword] = related_terms
            expanded_keywords.update(related_terms)
    
    if expanded_terms:
        logger.debug(f"知识图谱扩展详情: {json.dumps(expanded_terms, ensure_ascii=False, indent=2)}")
    
    logger.debug(f"知识图谱扩展后的关键词数量: {len(expanded_keywords)}")
    return list(expanded_keywords)

def identify_project_type(repo_data):
    """识别项目类型（课程、教程、演示、库、工具、应用、游戏、研究等）"""
    project_type = 'unknown'
    confidence = 0.0
    
    # 获取项目名称和描述
    name = repo_data.get('repo_name', '')
    description = repo_data.get('repo_description', '')
    
    # 添加空值检查
    if name is None:
        name = ''
    if description is None:
        description = ''
        
    name = name.lower()
    description = description.lower()
    text = f"{name} {description}"
    
    for type_name, patterns in PROJECT_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                project_type = type_name
                confidence = 0.7
                logger.debug(f"识别项目类型: {project_type} (匹配模式: {pattern})")
                break
        if confidence > 0:
            break
    
    # 使用主题标签增强识别
    if 'topics' in repo_data and repo_data.get('topics'):
        # 添加空值检查
        topics = []
        for topic in repo_data.get('topics', []):
            if topic is not None:  # 确保主题不是None
                topics.append(topic.lower())
            else:
                logger.warning("发现无效的主题标签：None")
                
        for topic in topics:
            for type_name, patterns in PROJECT_TYPE_PATTERNS.items():
                if any(re.search(pattern, topic) for pattern in patterns):
                    if confidence < 0.7 or project_type == 'unknown':
                        project_type = type_name
                        confidence = 0.8
                        logger.debug(f"从主题标签识别项目类型: {project_type} (主题: {topic})")
                    break
    
    return project_type, confidence

def extract_keywords(text):
    """从文本中提取技术关键词，使用spaCy进行处理，并应用高级启发式规则"""
    if not text:
        logger.debug("输入文本为空，无法提取关键词")
        return []
    
    logger.debug(f"正在处理文本: '{text[:100]}{'...' if len(text) > 100 else ''}'")
    
    # 预处理文本 - 替换连字符、特殊标点等
    text = text.lower()
    # 将CamelCase和snake_case拆分为独立单词
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # CamelCase拆分
    text = re.sub(r'_', ' ', text)  # snake_case拆分
    text = re.sub(r'-', ' ', text)  # kebab-case拆分
    
    # 使用spaCy进行文本处理
    doc = nlp(text)
    
    # 提取基础词汇
    filtered_tokens = []
    for token in doc:
        # 过滤停用词、标点符号和短词
        if (not token.is_stop and 
            not token.is_punct and 
            len(token.text) > 2 and
            token.text.strip() and
            token.text not in TECH_STOP_WORDS):
            filtered_tokens.append(token.text)
    
    logger.debug(f"基础词汇过滤后: {filtered_tokens}")
    
    # 提取技术特有的命名实体和短语
    tech_phrases = []
    
    # 技术词汇前缀和后缀
    tech_prefixes = ['api', 'sdk', 'lib', 'framework', 'tech', 'dev', 'cloud', 'data', 'ml', 'ai']
    tech_suffixes = ['js', 'py', 'ts', 'ui', 'db', 'app', 'kit', 'net', 'api', 'os']
    
    # 从命名实体中提取
    entities = []
    for ent in doc.ents:
        if ent.label_ in ["PRODUCT", "ORG", "GPE", "EVENT", "WORK_OF_ART"] and len(ent.text) > 2:
            tech_phrases.append(ent.text.lower())
            entities.append(f"{ent.text.lower()} ({ent.label_})")
    
    if entities:
        logger.debug(f"提取的命名实体: {entities}")
    
    # 从名词短语中提取
    noun_chunks = []
    for chunk in doc.noun_chunks:
        if len(chunk.text) > 2 and chunk.text.lower() not in TECH_STOP_WORDS:
            tech_phrases.append(chunk.text.lower())
            noun_chunks.append(chunk.text.lower())
    
    if noun_chunks:
        logger.debug(f"提取的名词短语: {noun_chunks}")
    
    # 提取技术词汇 (通过前缀和后缀识别)
    tech_identified = []
    for token in doc:
        token_text = token.text.lower()
        if (any(token_text.startswith(prefix) for prefix in tech_prefixes) or
            any(token_text.endswith(suffix) for suffix in tech_suffixes)):
            tech_phrases.append(token_text)
            tech_identified.append(token_text)
    
    if tech_identified:
        logger.debug(f"通过前缀或后缀识别的技术词汇: {tech_identified}")
    
    # 识别计算机科学课程代码
    course_codes = re.findall(r'\b[a-z]{2,4}\d{2,4}[a-z]?\b', text, re.IGNORECASE)
    if course_codes:
        logger.debug(f"识别到可能的课程代码: {course_codes}")
        tech_phrases.extend(course_codes)
    
    # 识别技术版本号
    version_patterns = re.findall(r'\b[a-z\-\.]+\d+\.\d+(?:\.\d+)?\b', text, re.IGNORECASE)
    if version_patterns:
        logger.debug(f"识别到可能的技术版本: {version_patterns}")
        tech_phrases.extend(version_patterns)
        
    # 检测复合技术术语 (通常是多个单词的专业术语)
    compound_terms = []
    for i in range(len(doc) - 1):
        if (not doc[i].is_stop and not doc[i+1].is_stop and 
            not doc[i].is_punct and not doc[i+1].is_punct):
            term = f"{doc[i].text.lower()} {doc[i+1].text.lower()}"
            if term not in TECH_STOP_WORDS and len(term) > 5:
                compound_terms.append(term)
    
    if compound_terms:
        logger.debug(f"识别到复合技术术语: {compound_terms}")
        tech_phrases.extend(compound_terms)
    
    # 合并所有关键词
    all_keywords = filtered_tokens + tech_phrases
    
    # 去重
    all_keywords = list(set(all_keywords))
    logger.debug(f"去重后的关键词总量: {len(all_keywords)}")
    
    # 直接匹配领域中的关键词
    domain_keywords = []
    for keyword in all_keywords:
        if keyword in KEYWORD_TO_DOMAIN:
            domain_keywords.append(keyword)
    
    if domain_keywords:
        logger.debug(f"直接匹配到领域中的关键词: {domain_keywords}")
    
    # 使用知识图谱增强关键词
    expanded_keywords = enhance_with_knowledge_graph(all_keywords)
    
    # 去重并返回
    unique_keywords = list(set(expanded_keywords))
    logger.info(f"最终提取到 {len(unique_keywords)} 个关键词")
    
    return unique_keywords

def map_keywords_to_domains(keywords):
    """将关键词映射到标准化的技术领域，使用改进的权重系统"""
    logger.debug(f"开始将 {len(keywords)} 个关键词映射到技术领域")
    
    domain_counts = Counter()
    direct_matches = {}  # 记录直接匹配的关键词
    partial_matches = {}  # 记录部分匹配的关键词
    
    # 关键词权重设置 - 根据关键词的特性给予不同权重
    keyword_weights = {
        # 核心技术和框架 - 高权重
        'react': 2.0, 'vue': 2.0, 'angular': 2.0, 'django': 2.0, 'spring': 2.0,
        'tensorflow': 2.0, 'pytorch': 2.0, 'kubernetes': 2.0, 'docker': 2.0,
        'ethereum': 2.0, 'gpt': 2.0, 'transformer': 2.0, 'unity': 2.0, 'unreal': 2.0,
        'opencv': 2.0, 'opengl': 2.0, 'vulkan': 2.0, 'directx': 2.0,
        
        # 编程语言 - 中等权重
        'javascript': 1.5, 'typescript': 1.5, 'python': 1.5, 'java': 1.5,
        'kotlin': 1.5, 'swift': 1.5, 'golang': 1.5, 'rust': 1.5, 'c++': 1.5,
        'c#': 1.5, 'ruby': 1.5, 'php': 1.5, 'scala': 1.5, 'dart': 1.5,
        
        # 通用技术术语 - 低权重
        'frontend': 1.0, 'backend': 1.0, 'mobile': 1.0, 'web': 1.0,
        'database': 1.0, 'cloud': 1.0, 'api': 1.0, 'server': 1.0, 'client': 1.0,
        
        # 课程和教育相关术语 - 专门权重
        'course': 2.5, 'assignment': 2.5, 'homework': 2.5, 'cs': 2.0, 'tutorial': 2.0
    }
    
    for keyword in keywords:
        # 直接映射
        if keyword in KEYWORD_TO_DOMAIN:
            domain = KEYWORD_TO_DOMAIN[keyword]
            # 应用关键词权重
            weight = keyword_weights.get(keyword, 1.0)
            domain_counts[domain] += weight
            
            # 记录匹配信息
            if domain not in direct_matches:
                direct_matches[domain] = []
            direct_matches[domain].append(f"{keyword} (权重={weight})")
        else:
            # # 判断是否是课程代码，如果是则直接映射到教育领域
            # if re.match(r'\b[a-z]{2,4}\d{2,4}[a-z]?\b', keyword, re.IGNORECASE):
            #     domain_counts['education'] += 2.5
            #     if 'education' not in direct_matches:
            #         direct_matches['education'] = []
            #     direct_matches['education'].append(f"{keyword} (课程代码, 权重=2.5)")
            #     continue
            
            # 部分匹配 - 更智能的匹配算法
            max_similarity = 0.0
            best_domain = None
            match_reason = ""
            
            for domain, domain_keywords in DOMAIN_MAPPINGS.items():
                for domain_keyword in domain_keywords:
                    # 计算关键词相似度 (简单实现，可以用更复杂的算法)
                    similarity = 0.0
                    reason = ""
                    
                    # 包含关系检查
                    if keyword in domain_keyword:
                        similarity = len(keyword) / len(domain_keyword) * 0.9
                        reason = f"包含于 {domain_keyword}"
                    elif domain_keyword in keyword:
                        similarity = len(domain_keyword) / len(keyword) * 0.8
                        reason = f"包含 {domain_keyword}"
                    # 前缀匹配
                    elif keyword.startswith(domain_keyword[:3]) and len(domain_keyword) >= 3:
                        similarity = 0.4
                        reason = f"前缀匹配 {domain_keyword}"
                    # 技术词汇扩展匹配
                    elif domain_keyword in TECH_KNOWLEDGE_GRAPH.get(keyword, []):
                        similarity = 0.7
                        reason = f"知识图谱关联 {domain_keyword}"
                    # 编辑距离检查 (简化版 - 仅检查第一个字符是否相同)
                    elif keyword[0] == domain_keyword[0] and abs(len(keyword) - len(domain_keyword)) <= 3:
                        similarity = 0.3
                        reason = f"与 {domain_keyword} 相似"
                    
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_domain = domain
                        match_reason = reason
            
            # 如果找到了较好的匹配，添加到领域权重中
            if max_similarity > 0.3 and best_domain:
                match_weight = max_similarity * 0.5  # 部分匹配给予较低权重
                domain_counts[best_domain] += match_weight
                
                # 记录匹配信息
                if best_domain not in partial_matches:
                    partial_matches[best_domain] = []
                partial_matches[best_domain].append(f"{keyword} ({match_reason}, 相似度={max_similarity:.2f}, 权重={match_weight:.2f})")
    
    # 记录匹配详情
    if direct_matches:
        logger.debug(f"直接匹配: {json.dumps(direct_matches, ensure_ascii=False)}")
    if partial_matches:
        logger.debug(f"部分匹配: {json.dumps(partial_matches, ensure_ascii=False)}")
    
    # 汇总结果
    for domain, count in domain_counts.items():
        logger.info(f"领域 '{domain}' 得分: {count:.2f}")
    
    return domain_counts

def analyze_repository(repo_data):
    """分析单个仓库，返回领域权重，使用综合的多信号分析系统"""
    # 添加数据有效性检查
    if not repo_data:
        logger.warning("无法分析空的仓库数据")
        return Counter()
        
    # 确保repo_name不为None
    repo_name = repo_data.get('repo_name', '未命名仓库')
    if repo_name is None:
        repo_name = '未命名仓库'
        logger.warning("发现仓库名为None，已替换为'未命名仓库'")
        
    logger.info(f"开始分析仓库: {repo_name}")
    
    # 识别项目类型
    project_type, type_confidence = identify_project_type(repo_data)
    logger.info(f"仓库类型识别: {project_type}, 置信度: {type_confidence:.2f}")
    
    domain_weights = Counter()
    
    # 配置各信号源权重 - 根据项目类型调整权重配置
    source_weights = {
        'repo_name': 2.0,      # 仓库名称是重要指标
        'repo_description': 1.5,  # 仓库描述提供详细信息
        'language': 2.5,       # 编程语言是最强指标
        'topics': 2.0,         # GitHub主题标签也很有指示性
        'readme': 1.0,         # README内容
    }
    
    # 根据项目类型调整权重
    if project_type == 'course' or project_type == 'tutorial':
        # 对于课程和教程，名称和描述更重要
        source_weights['repo_name'] = 2.5
        source_weights['repo_description'] = 2.0
        source_weights['language'] = 1.5  # 语言权重降低
    elif project_type == 'library' or project_type == 'tool':
        # 对于库和工具，语言和主题标签更重要
        source_weights['language'] = 3.0
        source_weights['topics'] = 2.5
    elif project_type == 'game':
        # 游戏开发项目特殊处理
        source_weights['repo_description'] = 2.0  # 描述中可能包含游戏引擎信息
    
    # 1. 分析仓库名称
    if repo_data.get('repo_name'):
        logger.info(f"分析仓库名称: {repo_data['repo_name']}")
        name_keywords = extract_keywords(repo_data['repo_name'])
        name_domains = map_keywords_to_domains(name_keywords)
        for domain, count in name_domains.items():
            weighted_count = count * source_weights['repo_name']
            domain_weights[domain] += weighted_count
            logger.debug(f"名称分析 - 领域 '{domain}' 得分: {weighted_count:.2f} (原始: {count:.2f} x 权重: {source_weights['repo_name']})")
    
    # 2. 分析仓库描述
    if repo_data.get('repo_description'):
        desc = repo_data['repo_description']
        logger.info(f"分析仓库描述: {desc[:100]}{'...' if len(desc) > 100 else ''}")
        desc_keywords = extract_keywords(desc)
        desc_domains = map_keywords_to_domains(desc_keywords)
        for domain, count in desc_domains.items():
            weighted_count = count * source_weights['repo_description']
            domain_weights[domain] += weighted_count
            logger.debug(f"描述分析 - 领域 '{domain}' 得分: {weighted_count:.2f} (原始: {count:.2f} x 权重: {source_weights['repo_description']})")
    
    # 3. 考虑编程语言权重
    if repo_data.get('language'):
        lang = repo_data['language'].lower()
        logger.info(f"分析编程语言: {lang}")
        
        # 3.1 首先使用多领域映射表 - 一种语言可以关联到多个领域
        if lang in LANGUAGE_TO_DOMAINS:
            domains = LANGUAGE_TO_DOMAINS[lang]
            logger.debug(f"语言 '{lang}' 关联到多个领域: {domains}")
            
            # 根据仓库特征调整语言相关领域的权重
            domain_weights_adjusted = False
            
            # # 特殊处理: 如果是课程项目且使用Java/Python等，增加教育领域的权重
            # if project_type == 'course' and lang in ['java', 'python', 'c++', 'c']:
            #     domain_weights['education'] += source_weights['language'] * 1.5
            #     domain_weights_adjusted = True
            #     logger.debug(f"课程项目使用 {lang}，增加教育领域权重")
            
            # 特殊处理: 如果是图形相关项目且使用C++/OpenGL等，增加图形学领域的权重
            graphics_indicators = ['render', 'graphic', 'shader', 'opengl', 'vulkan', 'directx', 'ray', 'shadow']
            if lang in ['c++', 'glsl', 'hlsl'] and any(indicator in repo_name.lower() or 
                                              (repo_data.get('repo_description') and indicator in repo_data['repo_description'].lower())
                                              for indicator in graphics_indicators):
                domain_weights['graphics'] += source_weights['language'] * 2.0
                domain_weights_adjusted = True
                logger.debug(f"图形相关项目使用 {lang}，增加图形学领域权重")
            
            # 如果没有特殊调整，则使用标准多领域映射
            if not domain_weights_adjusted:
                base_weight = source_weights['language'] / len(domains)
                for domain in domains:
                    domain_weights[domain] += base_weight
                    logger.debug(f"语言映射 - 领域 '{domain}' 得分: {base_weight:.2f}")
        else:
            # 3.2 尝试直接查找语言对应的领域
            lang_matched = False
            for domain, keywords in DOMAIN_MAPPINGS.items():
                if lang in keywords:
                    weighted_score = source_weights['language']
                    domain_weights[domain] += weighted_score
                    lang_matched = True
                    logger.debug(f"语言直接匹配 - 领域 '{domain}' 得分: {weighted_score:.2f}")
                    break
            
            # 3.3 如果没有直接匹配，尝试通过知识图谱关联
            if not lang_matched and lang in TECH_KNOWLEDGE_GRAPH:
                logger.debug(f"语言 '{lang}' 未直接匹配任何领域，尝试通过知识图谱关联")
                related_terms = TECH_KNOWLEDGE_GRAPH[lang]
                for term in related_terms:
                    if term in KEYWORD_TO_DOMAIN:
                        domain = KEYWORD_TO_DOMAIN[term]
                        weighted_score = source_weights['language'] * 0.7  # 间接匹配降低权重
                        domain_weights[domain] += weighted_score
                        logger.debug(f"语言通过知识图谱关联 '{term}' - 领域 '{domain}' 得分: {weighted_score:.2f}")
    
    # 4. 分析GitHub主题标签
    if repo_data.get('topics') and repo_data['topics']:
        topics = repo_data['topics']
        logger.info(f"分析GitHub主题标签: {topics}")
        for topic in topics:
            logger.debug(f"处理主题: {topic}")
            
            # 直接检查主题是否在领域关键词中
            if topic.lower() in KEYWORD_TO_DOMAIN:
                domain = KEYWORD_TO_DOMAIN[topic.lower()]
                weighted_score = source_weights['topics'] * 1.2  # 直接匹配给予额外奖励
                domain_weights[domain] += weighted_score
                logger.debug(f"主题直接匹配 - 领域 '{domain}' 得分: {weighted_score:.2f}")
                continue
            
            # 常规主题分析
            topic_keywords = extract_keywords(topic)
            topic_domains = map_keywords_to_domains(topic_keywords)
            for domain, count in topic_domains.items():
                weighted_count = count * source_weights['topics']
                domain_weights[domain] += weighted_count
                logger.debug(f"主题分析 - 领域 '{domain}' 得分: {weighted_count:.2f} (原始: {count:.2f} x 权重: {source_weights['topics']})")
    
    # # 5. 根据项目类型进行额外的领域权重调整
    # if project_type == 'course' or project_type == 'tutorial':
    #     # 教育和课程项目增加教育领域权重
    #     domain_weights['education'] += 5.0
    #     logger.debug(f"项目类型为 {project_type}，增加教育领域权重 +5.0")
    # elif project_type == 'game':
    #     # 游戏项目增加游戏开发领域权重
    #     domain_weights['gamedev'] += 5.0
    #     logger.debug(f"项目类型为 {project_type}，增加游戏开发领域权重 +5.0")
    
    # 6. 根据Star数量调整权重
    stars = repo_data.get('Star', 0)
    
    # 动态调整Star乘数，考虑项目类型
    star_multiplier = 1.0
    if project_type in ['course', 'tutorial', 'demo']:
        # 对于课程、教程和演示项目，Star的影响较小
        if stars > 1000:
            star_multiplier = 2.0
        elif stars > 100:
            star_multiplier = 1.5
        elif stars > 10:
            star_multiplier = 1.2
    else:
        # 对于其他项目，Star影响正常
        if stars > 1000:
            star_multiplier = 3.0
        elif stars > 100:
            star_multiplier = 2.0
        elif stars > 10:
            star_multiplier = 1.5
    
    logger.info(f"仓库星标数: {stars}, 星标权重乘数: {star_multiplier}")
    
    # 应用星标权重乘数
    original_weights = dict(domain_weights)
    for domain in domain_weights:
        domain_weights[domain] *= star_multiplier
        logger.debug(f"应用星标乘数 - 领域 '{domain}' 得分: {domain_weights[domain]:.2f} (原始: {original_weights[domain]:.2f} x 星标乘数: {star_multiplier})")
    
    # 输出最终分析结果
    logger.info(f"仓库 '{repo_name}' 的领域分析结果:")
    for domain, weight in sorted(domain_weights.items(), key=lambda x: x[1], reverse=True)[:5]:
        logger.info(f"  - {domain}: {weight:.2f}")
    
    return domain_weights

def get_repository_languages(username, repo_name):
    """获取仓库使用的编程语言及其比例"""
    logger.info(f"获取仓库 {username}/{repo_name} 的语言信息")
    
    try:
        url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
        logger.debug(f"请求URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"获取仓库 {username}/{repo_name} 语言信息失败，状态码: {response.status_code}")
            return {}
            
        languages = response.json()
        logger.debug(f"获取到原始语言数据: {languages}")
        
        total = sum(languages.values())
        
        # 计算每种语言的百分比
        language_percentages = {lang: (count / total) * 100 for lang, count in languages.items()}
        
        logger.info(f"仓库 {username}/{repo_name} 的语言分布: {json.dumps(language_percentages, indent=2)}")
        return language_percentages
        
    except Exception as e:
        logger.error(f"获取仓库 {username}/{repo_name} 语言信息时发生错误: {str(e)}")
        return {}

def get_repository_topics(username, repo_name):
    """获取仓库的主题标签"""
    logger.info(f"获取仓库 {username}/{repo_name} 的主题标签")
    
    try:
        url = f"https://api.github.com/repos/{username}/{repo_name}/topics"
        logger.debug(f"请求URL: {url}")
        
        # 需要特殊的Accept头部
        headers_with_topics = headers.copy()
        headers_with_topics['Accept'] = 'application/vnd.github.mercy-preview+json'
        
        response = requests.get(url, headers=headers_with_topics, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"获取仓库 {username}/{repo_name} 主题标签失败，状态码: {response.status_code}")
            return []
            
        topics = response.json().get('names', [])
        logger.info(f"仓库 {username}/{repo_name} 的主题标签: {topics}")
        return topics
        
    except Exception as e:
        logger.error(f"获取仓库 {username}/{repo_name} 主题标签时发生错误: {str(e)}")
        return []

def enrich_repo_data(username, repo_data):
    """增强仓库数据，添加语言和主题信息"""
    repo_name = repo_data.get('repo_name')
    if not repo_name:
        logger.warning("无法增强仓库数据：仓库名称缺失")
        return repo_data
    
    logger.info(f"开始增强仓库 {username}/{repo_name} 的数据")
    
    # 复制原数据以避免修改
    enriched_data = dict(repo_data)
    
    # 添加语言信息
    languages = get_repository_languages(username, repo_name)
    if languages:
        # 找出最主要的语言
        main_language = max(languages.items(), key=lambda x: x[1])[0]
        enriched_data['language'] = main_language
        enriched_data['language_percentages'] = languages
        logger.info(f"为仓库 {repo_name} 添加主要语言: {main_language} (占比 {languages[main_language]:.2f}%)")
    else:
        logger.warning(f"未能获取到仓库 {repo_name} 的语言信息")
    
    # 添加主题标签
    topics = get_repository_topics(username, repo_name)
    if topics:
        enriched_data['topics'] = topics
        logger.info(f"为仓库 {repo_name} 添加 {len(topics)} 个主题标签")
    else:
        logger.warning(f"未能获取到仓库 {repo_name} 的主题标签")
    
    return enriched_data

def get_developer_domains(username, repositories=None):
    """
    增强版: 分析开发者的技术领域
    
    参数:
    - username: 开发者用户名
    - repositories: 可选，预先获取的仓库数据列表
    
    返回:
    - 包含领域与评分的字典，以及各领域的置信度
    """
    try:
        logger.info(f"======= 开始分析开发者 '{username}' 的技术领域 =======")
        
        # 如果没有提供仓库数据，尝试获取
        if not repositories:
            try:
                # 尝试从user_profile模块导入get_user_repos函数
                try:
                    from user_profile import get_user_repos
                except ModuleNotFoundError:
                    try:
                        from src.user_profile import get_user_repos
                    except ModuleNotFoundError:
                        logger.error("无法导入user_profile模块，请确保它存在")
                        return {'error': 'user_profile模块不可用'}
                
                logger.info(f"从API获取开发者 '{username}' 的仓库数据")
                repositories = get_user_repos(username)
                logger.info(f"获取到开发者 '{username}' 的 {len(repositories)} 个仓库")
            except Exception as e:
                logger.error(f"获取开发者 '{username}' 的仓库信息失败: {str(e)}")
                return {'error': f'获取仓库数据失败: {str(e)}'}
        else:
            logger.info(f"使用预先提供的 {len(repositories)} 个仓库数据")
        
        if not repositories:
            logger.warning(f"开发者 '{username}' 没有可分析的仓库")
            return {}
        
        # 只分析开发者拥有的仓库
        owner_repos = [repo for repo in repositories if repo and repo.get("repo_type") == "owner"]
        logger.info(f"开发者 '{username}' 拥有 {len(owner_repos)} 个仓库用于分析")
        
        # 对每个仓库进行数据增强
        enriched_repos = []
        for idx, repo in enumerate(owner_repos, 1):
            try:
                # 确保repo数据有效
                if not repo:
                    logger.warning(f"跳过索引 {idx} 的空仓库数据")
                    continue
                    
                repo_name = repo.get('repo_name', f'未命名仓库-{idx}')
                if repo_name is None:
                    repo_name = f'未命名仓库-{idx}'
                    
                logger.info(f"增强仓库数据 [{idx}/{len(owner_repos)}]: {repo_name}")
                enriched_repo = enrich_repo_data(username, repo)
                enriched_repos.append(enriched_repo)
            except Exception as e:
                repo_name = repo.get('repo_name', f'未命名仓库-{idx}') if repo else f'未命名仓库-{idx}'
                logger.warning(f"增强仓库 {repo_name} 数据时出错: {str(e)}")
                if repo:  # 只有在repo不为None时才添加原始数据
                    enriched_repos.append(repo)  # 使用原始数据
        
        if not enriched_repos:
            logger.warning(f"开发者 '{username}' 没有可用的仓库数据进行分析")
            return {}
            
        # 领域分析结果
        domain_weights = Counter()
        domain_contributions = defaultdict(list)  # 记录每个领域的贡献来源和权重
        
        logger.info(f"开始分析 {len(enriched_repos)} 个仓库的技术领域")
        for idx, repo in enumerate(enriched_repos, 1):
            try:
                if not repo:
                    logger.warning(f"跳过索引 {idx} 的空仓库数据")
                    continue
                    
                repo_name = repo.get('repo_name', f'仓库-{idx}')
                if repo_name is None:
                    repo_name = f'仓库-{idx}'
                    
                logger.info(f"分析仓库 [{idx}/{len(enriched_repos)}]: {repo_name}")
                repo_domains = analyze_repository(repo)
                
                if not repo_domains:
                    logger.warning(f"仓库 {repo_name} 未返回任何领域数据")
                    continue
                
                # 根据仓库星数调整权重
                stars = repo.get('Star', 0)
                if stars is None:
                    stars = 0
                
                # 根据仓库活跃度和更新时间调整权重
                activity_weight = 1.0
                if 'last_update' in repo and repo['last_update']:
                    # 根据最后更新时间计算活跃度权重
                    # 这里简化处理，可以根据实际需求实现更复杂的逻辑
                    activity_weight = 1.0  # 默认权重
                
                # 计算复合权重，结合星标和活跃度
                repo_weight = 1.0 + (stars / 100) * activity_weight
                
                logger.info(f"仓库 '{repo_name}' 权重系数: {repo_weight:.2f} (星标: {stars}, 活跃度: {activity_weight:.2f})")
                
                for domain, weight in repo_domains.items():
                    adjusted_weight = weight * repo_weight
                    domain_weights[domain] += adjusted_weight
                    
                    # 记录贡献来源
                    domain_contributions[domain].append({
                        'repo': repo_name,
                        'weight': adjusted_weight,
                        'original_weight': weight,
                        'repo_weight': repo_weight
                    })
                    
                    logger.debug(f"累积领域权重 - '{domain}': +{adjusted_weight:.2f} (原始: {weight:.2f} x 仓库权重: {repo_weight:.2f})")
            except Exception as e:
                repo_name = repo.get('repo_name', f'仓库-{idx}') if repo else f'仓库-{idx}'
                logger.error(f"分析仓库 {repo_name} 时发生错误: {str(e)}")
        
        # 如果没有检测到任何领域，返回空
        if not domain_weights:
            logger.warning(f"未能检测到开发者 '{username}' 的技术领域")
            return {}
        
        # 领域权重汇总和计算置信度
        logger.info(f"开发者 '{username}' 的原始领域权重:")
        domain_confidence = {}
        
        # 计算总权重
        total_weight = sum(domain_weights.values())
        
        for domain, weight in sorted(domain_weights.items(), key=lambda x: x[1], reverse=True):
            # 计算领域置信度 - 基于权重在总权重中的占比以及贡献该领域的仓库数量
            contrib_repos = len(domain_contributions[domain])
            contrib_ratio = contrib_repos / len(enriched_repos)
            weight_ratio = weight / total_weight if total_weight > 0 else 0
            
            # 置信度计算公式: 0.6 * 权重比例 + 0.4 * 贡献仓库比例
            confidence = 0.6 * weight_ratio + 0.4 * contrib_ratio
            domain_confidence[domain] = round(confidence * 100, 1)  # 转换为百分比
            
            logger.info(f"  - {domain}: 权重={weight:.2f}, 占比={weight_ratio:.2f}, 涉及仓库数={contrib_repos}, 置信度={domain_confidence[domain]}")
        
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
        
        # 为返回结果添加置信度信息
        result = {
            'domains': top_domains,
            'confidence': {domain: domain_confidence[domain] for domain in top_domains}
        }
        
        logger.info(f"分析完成，开发者 '{username}' 的主要技术领域:")
        for domain, score in top_domains.items():
            logger.info(f"  - {domain}: 得分={score}, 置信度={domain_confidence[domain]}%")
        
        logger.info(f"======= 开发者 '{username}' 的技术领域分析完成 =======")
        return top_domains  # 直接返回领域字典，而不是嵌套结构
    except Exception as e:
        logger.error(f"分析开发者 '{username}' 的技术领域时发生严重错误: {str(e)}", exc_info=True)
        # 返回空字典而不是引发异常，确保API能够继续工作
        return {}

# 如果直接运行该模块，执行以下测试代码
if __name__ == "__main__":
    # 设置日志级别为DEBUG以查看更多信息
    logging.getLogger(__name__).setLevel(logging.DEBUG)
    
    # 测试数据 - 模拟的仓库数据
    test_repositories = [
        {
            "repo_type": "owner",
            "repo_name": "test-repo-1",
            "repo_description": "一个React和Node.js的测试项目",
            "language": "JavaScript",
            "topics": ["react", "nodejs", "web-development"],
            "Star": 20
        },
        {
            "repo_type": "owner",
            "repo_name": "test-repo-2",
            "repo_description": "Python机器学习测试",
            "language": "Python",
            "topics": ["machine-learning", "tensorflow", "data-science"],
            "Star": 15
        },
        {
            "repo_type": "owner",
            "repo_name": "shadow-mapping",
            "repo_description": "OpenGL实现的阴影映射算法",
            "language": "C++",
            "topics": ["graphics", "opengl", "shader", "rendering"],
            "Star": 30
        },
        {
            "repo_type": "owner",
            "repo_name": "CS61B-exercises",
            "repo_description": "数据结构课程练习",
            "language": "Java",
            "topics": ["course", "data-structures", "algorithms", "education"],
            "Star": 5
        }
    ]
    
    # 测试使用模拟数据
    print("测试1：使用模拟数据分析领域")
    result = get_developer_domains("test-user", test_repositories)
    print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 测试异常情况 - 空仓库列表
    print("\n测试2：空仓库列表")
    result = get_developer_domains("test-user", [])
    print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 测试异常情况 - 包含None的仓库
    print("\n测试3：包含None的仓库列表")
    corrupted_repos = test_repositories.copy()
    corrupted_repos.insert(1, None)
    result = get_developer_domains("test-user", corrupted_repos)
    print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # 测试异常情况 - 包含缺少关键字段的仓库
    print("\n测试4：包含缺少关键字段的仓库")
    incomplete_repos = test_repositories.copy()
    incomplete_repos.append({"repo_type": "owner", "Star": 10})  # 没有repo_name
    result = get_developer_domains("test-user", incomplete_repos)
    print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    print("\n所有测试完成！") 