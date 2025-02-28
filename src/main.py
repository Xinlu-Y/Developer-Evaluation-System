from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime
from developer_analyzer import (get_user_profile_nation_detect, get_user_repos,
                                get_user_total_stars)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('search.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 启用CORS  

@app.route('/api/developer/<username>', methods=['GET'])
def get_developer_info(username):
    """获取开发者详细信息的API端点"""
    try:
        # 获取开发者基本信息
        developer_data = get_user_profile_nation_detect(username)
        if not developer_data:
            return jsonify({"error": "未找到该用户"}), 404
            
        # 获取用户仓库信息
        user_repo = get_user_repos(username)
        
        # 获取贡献信息
        contribution_data = get_user_contributed_repos(username)
        contribution_score = evaluate_overall_contribution(contribution_data)
        
        # 获取star总数
        total_stars = get_user_total_stars(username)
        
        # 计算评分
        talent_rank_score = calculate_talent_rank(
            total_stars, 
            developer_data['关注者数'], 
            contribution_score
        )
        
        # 构建响应数据
        response_data = {
            "profile": developer_data,
            "repositories": user_repo,
            "contributions": contribution_data,
            "total_stars": total_stars,
            "talent_rank_score": talent_rank_score
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
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
        limit = int(request.args.get('limit', 10))  
        
        # 执行搜索
        results = search_repositories_by_language_and_topic(language, topic, offset, limit)
        
        # 记录搜索结束
        end_time = datetime.now()   
        
        # 构建响应数据
        response_data = {
            "results": results,
            "total": total_results,
            "duration": end_time - start_time
        }   
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "未找到请求的资源"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "服务器内部错误"}), 500

if __name__ == '__main__':
    app.run(debug=True)