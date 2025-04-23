import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime
from contribution_analysis import calculate_talent_rank, evaluate_overall_contribution, get_user_contributed_repos
from country_prediction import predict_developer_country
from domain_analysis import get_developer_domains_weighted, convert_numpy
from geo_utils import get_country_name
from search_utils import search_repositories_by_language_and_topic
from user_profile import (get_user_repos, get_user_total_stars)  
from developer_profile_crawler import collect_developer_data
from data_processor import process_developer_data
from retrieval import retrieve_relevant_information, generate_skill_summary, generate_search_queries

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('search.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        if hasattr(handler.stream, 'encoding') and handler.stream.encoding != 'utf-8':
            try:
                import codecs
                handler.stream = codecs.getwriter('utf-8')(handler.stream)
            except:
                pass

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 启用CORS

@app.route('/api/developer/<username>', methods=['GET'])
def get_developer_info(username):
    """获取单个开发者的详细信息"""
    try:
        logger.info(f"开始获取开发者信息: '{username}'")
        
        # 获取国家预测信息
        country_prediction = predict_developer_country(username)       
        
        # 获取仓库信息
        try:
            user_repo = get_user_repos(username)
            owner_repos = [repo for repo in user_repo if repo["repo_type"] == "owner"]
            member_repos = [repo for repo in user_repo if repo["repo_type"] == "member"]
            logger.info(f"获取到用户 '{username}' 的仓库信息: {len(user_repo)} 个仓库")
        except Exception as e:
            logger.warning(f"获取用户 '{username}' 的仓库信息失败: {str(e)}")
            user_repo = []
            owner_repos = []
            member_repos = []
        
        # 获取贡献信息
        try:
            contribution_data = get_user_contributed_repos(username)
            logger.info(f"获取到用户 '{username}' 的贡献信息")
            contribution_score = evaluate_overall_contribution(contribution_data)
        except Exception as e:
            logger.warning(f"获取用户 '{username}' 的贡献信息失败: {str(e)}")
            contribution_data = []
            contribution_score = 0
        
        # 获取star总数
        try:
            total_stars = get_user_total_stars(username)
            logger.info(f"获取到用户 '{username}' 的star总数: {total_stars}")
        except Exception as e:
            logger.warning(f"获取用户 '{username}' 的star总数失败: {str(e)}")
            total_stars = 0
        
        # 计算TalentRank评分
        followers_count = 0
        if country_prediction and country_prediction.get("profile_location"):
            followers_count = country_prediction.get("profile_location", {}).get("关注者数", 0)
        
        talent_rank_score = calculate_talent_rank(
            total_stars,
            followers_count,
            contribution_score
        )
        logger.info(f"计算用户 '{username}' 的TalentRank评分: {talent_rank_score}")
        
        # 处理国家预测结果，确保即使在低置信度时也能显示预测结果
        prediction = country_prediction.get("prediction", {})
        
        # 如果预测结果存在但置信度低，添加额外的显示信息
        if prediction and prediction.get("predicted_country") != "Unknown":
            confidence = prediction.get("confidence", 0)
            confidence_level = prediction.get("confidence_level", "低")
            
            # 添加格式化的预测结果，包含置信度信息
            country_code = prediction.get("predicted_country")
            country_name = get_country_name(country_code)
            
            # 添加格式化的预测结果字段
            prediction["formatted_prediction"] = f"{country_name} ({confidence_level}置信度: {confidence:.2f})"
            
            # 添加是否应该显示预测结果的标志
            # 即使置信度低，也显示预测结果，但标记为低置信度
            prediction["should_display"] = True
            
            logger.info(f"用户 '{username}' 的国家预测结果已格式化: {prediction['formatted_prediction']}")
        
        # 分析开发者技术领域
        try:
            domains = get_developer_domains_weighted(username, user_repo,
                                                    apply_tfidf=True,
                                                    apply_softmax=True,
                                                    softmax_temp=0.5)
            logger.info(f"获取到用户 '{username}' 的技术领域: {domains}")
        except Exception as e:
            logger.warning(f"分析用户 '{username}' 的技术领域失败: {str(e)}")
            domains = {}

        response_data = {
            "username": username,
            "profile": country_prediction.get("profile_location", {}),
            "country_prediction": prediction,
            "timezone_analysis": country_prediction.get("timezone_analysis", {}),
            "language_culture": country_prediction.get("language_culture", {}),
            "repositories": owner_repos,
            "contributions": member_repos,
            "total_stars": total_stars,
            "talent_rank_score": talent_rank_score,
            "domains": convert_numpy(domains)
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"获取开发者信息时发生错误: {str(e)}", exc_info=True)
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
        query = request.args.get('query', '技术能力分析')
        
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
        sorted_results = sorted(unique_results, key=lambda x: x["score"])
        
        # 最多取前10个结果
        top_results = sorted_results[:10]
        
        # 生成技术能力总结
        summary_result = generate_skill_summary(username, top_results)
        
        return jsonify({
            "username": username,
            "query": query,
            "expanded_queries": queries,
            "skill_summary": summary_result["summary"],
            "model": summary_result["model"],
            "search_results": top_results
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
                country_prediction = predict_developer_country(username)
                
                # 即使没有完整的profile_location，也尝试获取其他信息
                user_repo = []
                contribution_data = []
                contribution_score = 0
                total_stars = 0
                
                # 尝试获取仓库信息
                try:
                    user_repo = get_user_repos(username)
                    owner_repos = [repo for repo in user_repo if repo["repo_type"] == "owner"]
                    member_repos = [repo for repo in user_repo if repo["repo_type"] == "member"]
                    logger.info(f"获取到 {username} 的仓库信息: {len(user_repo)} 个仓库")
                except Exception as e:
                    logger.warning(f"获取 {username} 的仓库信息失败: {str(e)}")
                
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
                if country_prediction and country_prediction.get("profile_location"):
                    followers_count = country_prediction.get("profile_location", {}).get("关注者数", 0)
                
                talent_rank_score = calculate_talent_rank(
                    total_stars,
                    followers_count,
                    contribution_score
                )
                logger.info(f"{username} 的 TalentRank 评分: {talent_rank_score}")
                
                # 分析开发者技术领域
                try:
                    domains = get_developer_domains(username, user_repo)
                    logger.info(f"获取到用户 '{username}' 的技术领域: {domains}")
                except Exception as e:
                    logger.warning(f"分析用户 '{username}' 的技术领域失败: {str(e)}")
                    domains = {}
                
                # 如果请求包含技能分析，尝试获取技术能力总结
                skill_summary = None
                if include_skills:
                    try:
                        from config import DOWNLOAD_DIR
                        vector_store_path = os.path.join(DOWNLOAD_DIR, f"{username}_vector_store")
                        
                        # 检查是否已有向量存储，如果有则生成技术能力总结
                        if os.path.exists(vector_store_path):
                            logger.info(f"为开发者 '{username}' 预加载技术能力总结")
                            
                            # 使用简短的查询生成技术能力摘要
                            queries = generate_search_queries("技术能力简介")
                            all_results = []
                            for q in queries[:2]:  # 只使用前两个查询，减少处理时间
                                results = retrieve_relevant_information(username, q, top_k=5)  # 减少结果数量
                                all_results.extend(results)
                            
                            # 去重并排序
                            unique_contents = set()
                            unique_results = []
                            for result in all_results:
                                content = result["content"]
                                if content not in unique_contents:
                                    unique_contents.add(content)
                                    unique_results.append(result)
                            
                            sorted_results = sorted(unique_results, key=lambda x: x["score"])
                            top_results = sorted_results[:5]  # 只取前5个结果
                            
                            # 生成简短的技术能力总结
                            skill_summary_result = generate_skill_summary(username, top_results)
                            skill_summary = skill_summary_result["summary"]
                            model_name = skill_summary_result["model"]
                        else:
                            logger.info(f"开发者 '{username}' 没有向量存储，跳过技术能力总结生成")
                    except Exception as e:
                        logger.warning(f"为开发者 '{username}' 生成技术能力总结时发生错误: {str(e)}")
                
                # 即使部分数据缺失，也构建开发者信息
                developer_info = {
                    "profile": {} if not country_prediction else country_prediction.get("profile_location", {}),
                    "country_prediction": {"predicted_country": "Unknown", "confidence": 0} if not country_prediction else country_prediction.get("prediction", {}),
                    "timezone_analysis": {} if not country_prediction else country_prediction.get("timezone_analysis", {}),
                    "language_culture": {} if not country_prediction else country_prediction.get("language_culture", {}),
                    "repositories": owner_repos,
                    "contributions": member_repos,
                    "total_stars": total_stars,
                    "talent_rank_score": talent_rank_score,
                    "domains": domains
                }
                
                # 添加技术能力总结（如果有）
                if skill_summary:
                    developer_info["skill_summary"] = skill_summary
                    developer_info["model"] = model_name
                
                developers.append(developer_info)
            except Exception as e:
                logger.error(f"处理开发者 {username} 时发生错误: {str(e)}", exc_info=True)
                # 添加一个带有错误信息的占位开发者条目
                developers.append({
                    "username": username,
                    "error": f"处理数据时发生错误: {str(e)}",
                    "profile": {},
                    "country_prediction": {"predicted_country": "Unknown", "confidence": 0},
                    "repositories": [],
                    "contributions": [],
                    "total_stars": 0,
                    "talent_rank_score": 0,
                    "domains": {}
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