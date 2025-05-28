import os
import json
import logging
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_caching import Cache

from langsmith import Client, traceable
from langsmith.utils import LangSmithConflictError

from contribution_analysis import (
    calculate_talent_rank,
    evaluate_overall_contribution,
    get_user_contributed_repos
)
from country_prediction import predict_developer_country
from domain_analysis import (
    get_developer_domains_weighted,
    convert_numpy,
    aggregate_language_characters
)
from geo_utils import get_country_name
from search_utils import search_repositories_by_language_and_topic
from user_profile import get_user_repos, get_user_total_stars, get_user_profile
from developer_profile_crawler import collect_developer_data
from data_processor import process_developer_data
from retrieval import (
    retrieve_relevant_information,
    generate_skill_summary,
    generate_search_queries
)
from rag_evaluation import helpfulness


# ——— Logging 配置 ———
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('search.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

client = Client()
dataset_name = "Developer Skill Summary"

try:
    dataset = client.create_dataset(dataset_name)
    
except LangSmithConflictError:
    all_datasets = client.list_datasets()
    dataset = next(ds for ds in all_datasets if ds.name == dataset_name)

    # 把 generator 转为 list
    existing_examples = list(client.list_examples(dataset_id=dataset.id))
    if existing_examples:
        print(f"数据集 '{dataset_name}' 已存在且包含 {len(existing_examples)} 条数据。")
        print("无参考模式下，这些数据不会被用于评估。")
    else:
        print(f"数据集 '{dataset_name}' 已存在，当前为空。")

# ——— Flask 应用 & CORS ———
app = Flask(__name__)
CORS(app)

# ——— Flask-Caching 配置 ———
app.config.from_mapping({
    "CACHE_TYPE": "filesystem",          # 可选 "simple", "redis" 等
    "CACHE_DIR": "flask_cache",          # filesystem 时的缓存目录
    "CACHE_DEFAULT_TIMEOUT": 3600        # 默认 1 小时
})
cache = Cache(app)


# ——— 缓存封装函数 ———

@cache.memoize(timeout=3600)
def predict_country_cached(username):
    """对 predict_developer_country(username) 缓存 1 小时"""
    return predict_developer_country(username)


@cache.memoize(timeout=1800)
def analyze_domains_cached(username, owner_repos_json):
    """
    对领域分析做缓存，缓存 30 分钟。
    参数 owner_repos_json: JSON 字符串形式的 owner_repos 列表。
    """
    owner_repos = json.loads(owner_repos_json)
    domains = get_developer_domains_weighted(
        username,
        owner_repos,
        apply_tfidf=True,
        apply_softmax=True,
        softmax_temp=0.5
    )
    stats = aggregate_language_characters(owner_repos)
    return convert_numpy(domains), stats


# ——— API：获取单个开发者信息 ———

@app.route('/api/developer/<username>', methods=['GET'])
def get_developer_info(username):
    try:
        logger.info(f"开始获取开发者信息: '{username}'")

        # 1. 国家预测（从缓存取或计算）
        country_prediction = predict_country_cached(username)

        # 2. 获取仓库列表
        user_repo = get_user_repos(username)
        owner_repos = [r for r in user_repo if r["repo_type"] == "owner"]
        member_repos = [r for r in user_repo if r["repo_type"] == "member"]
        logger.info(f"获取到用户 '{username}' 的仓库: {len(user_repo)} 个")

        # 3. 领域分析（从缓存取或计算）
        owner_json = json.dumps(owner_repos, sort_keys=True, default=str)
        domains, language_character_stats = analyze_domains_cached(username, owner_json)
        logger.info(f"获取到用户 '{username}' 的领域分析结果")

        # 4. 贡献信息
        contribution_data = get_user_contributed_repos(username)
        contribution_score = evaluate_overall_contribution(contribution_data)

        # 5. Star 总数
        total_stars = get_user_total_stars(username)

        # 6. TalentRank 评分
        followers_count = (
            country_prediction.get("profile_location", {})
            .get("关注者数", 0)
        )
        talent_rank_score = calculate_talent_rank(
            total_stars, followers_count, contribution_score
        )

        # 7. 格式化国家预测输出
        prediction = country_prediction.get("prediction", {})
        if prediction.get("predicted_country") != "Unknown":
            code = prediction["predicted_country"]
            name = get_country_name(code)
            conf = prediction.get("confidence", 0)
            level = prediction.get("confidence_level", "低")
            prediction["formatted_prediction"] = (
                f"{name} ({level} 置信度: {conf:.2f})"
            )
            prediction["should_display"] = True

        # 8. 返回 JSON
        return jsonify({
            "username": username,
            "profile": country_prediction.get("profile_location", {}),
            "country_prediction": prediction,
            "timezone_analysis": country_prediction.get("timezone_analysis", {}),
            "language_culture": country_prediction.get("language_culture", {}),
            "repositories": owner_repos,
            "contributions": member_repos,
            "total_stars": total_stars,
            "talent_rank_score": talent_rank_score,
            "domains": domains,
            "language_character_stats": language_character_stats
        })

    except Exception as e:
        logger.error(f"获取开发者信息失败: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "message": "服务器处理请求时发生错误",
            "username": username,
            "profile": {},
            "country_prediction": {"predicted_country": "Unknown", "confidence": 0},
            "domains": {}
        }), 500

@app.route('/api/developer/skills/<username>', methods=['GET'])
def analyze_developer_skills(username):
    """分析开发者的技术能力"""
    try:
        logger.info(f"开始分析开发者技术能力: '{username}'")
        
        # 检查是否已有向量存储
        from config import DOWNLOAD_DIR
        vector_store_path = os.path.join(DOWNLOAD_DIR, f"{username}_vector_store")
        
        # 如果没有现成的向量存储，则需要收集和处理数据
        if not os.path.exists(vector_store_path):
            logger.info(f"未找到开发者 '{username}' 的向量存储，开始收集数据")
            
            # 收集开发者数据
            developer_data = collect_developer_data(username)
            if not developer_data:
                return jsonify({
                    "error": "无法获取开发者数据",
                    "username": username,
                    "skill_summary": "无法获取开发者数据，请稍后再试"
                }), 500
            
            # 处理数据并创建向量存储
            processing_result = process_developer_data(username, developer_data)
            if not processing_result:
                return jsonify({
                    "error": "处理开发者数据失败",
                    "username": username,
                    "skill_summary": "处理开发者数据失败，请稍后再试"
                }), 500
                
            logger.info(f"成功创建开发者 '{username}' 的向量存储: {processing_result['document_count']} 个文档")
        else:
            logger.info(f"找到开发者 '{username}' 的现有向量存储")
        
        # 获取用户查询
        query = request.args.get('query', '技术能力分析总结')
        
        # 生成扩展查询
        queries = generate_search_queries(query)
        
        # 合并所有查询的结果
        all_results = []
        for q in queries:
            results = retrieve_relevant_information(username, q)
            all_results.extend(results)
        
        # 去重（基于内容）
        unique_contents = set()
        unique_results = []
        for result in all_results:
            content = result["content"]
            if content not in unique_contents:
                unique_contents.add(content)
                unique_results.append(result)
        
        # 根据相关性排序
        sorted_results = sorted(unique_results, key=lambda x: x["score"], reverse=True)
        
        # 最多取前10个结果
        top_results = sorted_results[:10]
        
        context = ""
        seen_hashes = set()
        for result in top_results:
            source = result["metadata"].get("source", "Unknown")
            content = result["content"]
            h = hash(content)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            context += f"===来源: {source}===\n{content}\n\n"
        summary_result = generate_skill_summary(username, context)

        # 注释部分用于LangSmith评估器评估LLM生成的总结内容
        # @traceable
        # def skill_summary_fn(inputs: dict) -> dict:
        #     username = inputs["username"]
        #     context  = inputs["context"]
        #     return generate_skill_summary(username, context)
        
        # evaluation = client.evaluate(
        #     skill_summary_fn,
        #     data=dataset.id,
        #     evaluators=[helpfulness],
        #     experiment_prefix="SkillSummaryGenEval",
        #     max_concurrency=0,
        # )

        # for result in evaluation:
        #     print("FULL RESULT DICT:", result)
        #     print("AVAILABLE KEYS:", list(result.keys()))
        #     break


        return jsonify({
            "username": username,
            "query": query,
            "expanded_queries": queries,
            "search_results": top_results,
            "skill_summary": summary_result["summary"],
            "model": summary_result["model"],
            "search_results": top_results,
        })
        
    except Exception as e:
        logger.error(f"分析开发者技术能力时发生错误: {str(e)}", exc_info=True)
        return jsonify({
            "error": str(e),
            "message": "分析开发者技术能力时发生错误",
            "username": username,
            "skill_summary": f"分析过程中发生错误: {str(e)}"
        }), 500

@app.route('/api/search/domain', methods=['GET'])
def search_by_domain():
    """基于领域搜索开发者的API端点"""
    try:
        # 记录搜索开始
        start_time = datetime.now()
        
        # 获取查询参数
        language = request.args.get('language', '')
        topic = request.args.get('topic', '')
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 5))
        include_skills = request.args.get('include_skills', 'false').lower() == 'true'
        
        logger.info(f"开始领域搜索 - 语言: {language}, 主题: {topic}, 偏移量: {offset}, 限制: {limit}, 包含技能: {include_skills}")
        
        if not language or not topic:
            logger.warning("搜索参数不完整")
            return jsonify({"error": "必须提供language和topic参数"}), 400
            
        # 根据当前页码计算需要获取的结果数量
        max_results = offset + limit
        logger.info("正在搜索符合条件的仓库...")
        usernames = search_repositories_by_language_and_topic(
            language,
            topic,
            max_results=max_results
        )
        
        if not usernames:
            logger.info("未找到符合条件的开发者")
            return jsonify({"developers": [], "total": 0})
            
        logger.info(f"找到 {len(usernames)} 个潜在开发者")
        
        # 只处理当前分页需要的用户
        page_usernames = usernames[offset:offset + limit]
        developers = []
        
        # 获取每个开发者的详细信息
        for idx, username in enumerate(page_usernames, 1):
            logger.info(f"正在处理第 {idx}/{len(page_usernames)} 个开发者: {username}")
            
            try:
                # 使用新的国家预测功能
                # country_prediction = predict_developer_country(username)
                profile = get_user_profile(username)
                # country_prediction = {
                #     "profile_location": {},
                #     "prediction": {"predicted_country": "Unknown", "confidence": 0},
                #     "timezone_analysis": {},
                #     "language_culture": {}
                # }
                
                # 尝试获取仓库信息
                try:
                    user_repo = get_user_repos(username)
                    owner_repos = [repo for repo in user_repo if repo["repo_type"] == "owner"]
                    member_repos = [repo for repo in user_repo if repo["repo_type"] == "member"]
                    logger.info(f"获取到 {username} 的仓库信息: {len(user_repo)} 个仓库")
                except Exception as e:
                    logger.warning(f"获取 {username} 的仓库信息失败: {str(e)}")
                    owner_repos = []
                    member_repos = []

                # 尝试获取贡献信息
                try:
                    contribution_data = get_user_contributed_repos(username)
                    logger.info(f"获取到 {username} 的贡献信息")
                    contribution_score = evaluate_overall_contribution(contribution_data)
                except Exception as e:
                    logger.warning(f"获取 {username} 的贡献信息失败: {str(e)}")
                
                # 尝试获取star总数
                try:
                    total_stars = get_user_total_stars(username)
                except Exception as e:
                    logger.warning(f"获取 {username} 的star总数失败: {str(e)}")
                
                # 计算TalentRank评分
                followers_count = 0
                followers_count = profile.get("关注者数", 0)
                
                talent_rank_score = calculate_talent_rank(
                    total_stars,
                    followers_count,
                    contribution_score
                )
                logger.info(f"{username} 的 TalentRank 评分: {talent_rank_score}")
                
                # 分析开发者技术领域
                try:
                    domains = get_developer_domains_weighted(username, owner_repos,
                                                            apply_tfidf=True,
                                                            apply_softmax=True,
                                                            softmax_temp=0.5)
                    language_character_stats = aggregate_language_characters(owner_repos)
                    logger.info(f"用户 '{username}' 的技术领域详细信息:\n{json.dumps(convert_numpy(domains), indent=2, ensure_ascii=False)}")
                except Exception as e:
                    logger.warning(f"分析用户 '{username}' 的技术领域失败: {str(e)}")
                    domains = {}
                    language_character_stats = {}
                
                developer_info = {
                    "username": username,
                    "profile": profile,
                    # "country_prediction": {"predicted_country": "Unknown", "confidence": 0} if not country_prediction else country_prediction.get("prediction", {}),
                    # "timezone_analysis": {} if not country_prediction else country_prediction.get("timezone_analysis", {}),
                    # "language_culture": {} if not country_prediction else country_prediction.get("language_culture", {}),
                    "repositories": owner_repos,
                    "contributions": member_repos,
                    "total_stars": total_stars,
                    "talent_rank_score": talent_rank_score,
                    "domains": convert_numpy(domains),
                    "language_character_stats" : language_character_stats
                }
                developers.append(developer_info)
            except Exception as e:
                logger.error(f"处理开发者 {username} 时发生错误: {str(e)}", exc_info=True)
                # 添加一个带有错误信息的占位开发者条目
                developers.append({
                    "username": username,
                    "error": f"处理数据时发生错误: {str(e)}",
                    "profile": {},
                    # "country_prediction": {"predicted_country": "Unknown", "confidence": 0},
                    "repositories": [],
                    "contributions": [],
                    "total_stars": 0,
                    "talent_rank_score": 0,
                    "domains": {},
                    "language_character_stats" : {}
                })
        
        # 按TalentRank评分排序（只排序当前页的数据）
        developers.sort(key=lambda x: x.get("talent_rank_score", 0), reverse=True)
        
        # 记录搜索完成时间
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"搜索完成，耗时: {duration:.2f} 秒，找到 {len(developers)} 个开发者")
        
        response_data = {
            "developers": developers,
            "total": len(usernames),
            "offset": offset,
            "limit": limit,
            "search_time": f"{duration:.2f}",
            "include_skills": include_skills
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"搜索过程中发生错误: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "message": "搜索过程中发生错误", "developers": []}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "未找到请求的资源"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "服务器内部错误"}), 500

if __name__ == '__main__':
    app.run(debug=True)