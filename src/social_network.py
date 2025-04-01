import logging
import requests
from config import headers
from contribution_analysis import get_user_contributed_repos
from user_profile import get_user_repos

def analyze_social_network(username, depth=2):
    """深入分析用户的社交网络，包括合作者和共同关注者"""
    logger = logging.getLogger(__name__)
    logger.info(f"开始分析用户 '{username}' 的社交网络，深度设置为{depth}")
    
    location_weights = {}
    processed_users = set()  # 记录已处理的用户，避免重复处理
    processed_users.add(username)  # 先添加目标用户
    
    # 递归分析社交网络
    _analyze_network_level(username, location_weights, processed_users, current_depth=1, max_depth=depth, logger=logger)
    
    # 获取用户作为member的仓库信息
    try:
        # 获取用户所有仓库
        all_repos = get_user_repos(username)
        # 筛选出用户作为member的仓库
        member_repos = [repo for repo in all_repos if repo["repo_type"] == "member"]
        logger.info(f"获取到用户 '{username}' 作为member的仓库: {len(member_repos)} 个")
        
        for repo_info in member_repos:
            try:
                repo_name = repo_info["repo_name"]
                # 获取完整的仓库名称（包含所有者）
                repo_full_name = None
                
                # 从html_url中获取完整仓库名称
                html_url = repo_info.get("html_url", "")
                if html_url and "github.com/" in html_url:
                    parts = html_url.split("github.com/")
                    if len(parts) > 1:
                        repo_full_name = parts[1]
                
                if not repo_full_name:
                    logger.warning(f"无法从仓库信息中获取完整仓库名称，跳过仓库 '{repo_name}'")
                    continue
                
                contributors_url = f"https://api.github.com/repos/{repo_full_name}/contributors"
                contributors_response = requests.get(contributors_url, headers=headers, timeout=10)
                
                if contributors_response.status_code != 200:
                    logger.warning(f"请求仓库 '{repo_full_name}' 的贡献者失败，状态码: {contributors_response.status_code}")
                    continue
                    
                contributors = contributors_response.json()
                logger.info(f"仓库 '{repo_full_name}' 共有 {len(contributors)} 个贡献者")
                
                for contributor in contributors:
                    if contributor.get("login") != username:
                        try:
                            contributor_name = contributor.get('login')
                            contributor_profile_url = f"https://api.github.com/users/{contributor_name}"
                            contributor_profile_response = requests.get(contributor_profile_url, headers=headers, timeout=10)
                            
                            if contributor_profile_response.status_code == 200:
                                contributor_data = contributor_profile_response.json()
                                location = contributor_data.get("location")
                                
                                if location and not any(char in location for char in ['#', '%', '&', '*', '乱码']):
                                    logger.info(f"贡献者 '{contributor_name}' 的位置: {location}, 权重: 1.5")
                                    if location in location_weights:
                                        location_weights[location] += 1.5  # 共同贡献者权重为1.5
                                    else:
                                        location_weights[location] = 1.5
                        except Exception as e:
                            logger.warning(f"处理贡献者 '{contributor_name}' 时发生错误: {str(e)}")
                            continue
            except Exception as e:
                logger.warning(f"处理仓库 '{repo_name}' 时发生错误: {str(e)}")
                continue
    except Exception as e:
        logger.warning(f"获取用户 '{username}' 的member仓库时发生错误: {str(e)}")
    
    # 返回按权重排序的位置列表
    result = sorted(location_weights.items(), key=lambda x: x[1], reverse=True)
    logger.info(f"完成用户 '{username}' 的社交网络分析，找到 {len(location_weights)} 个不同位置")
    return result

def _analyze_network_level(username, location_weights, processed_users, current_depth, max_depth, logger):
    """递归分析社交网络层级"""
    if current_depth > max_depth:
        return
    
    logger.info(f"分析第 {current_depth} 层社交网络: 用户 '{username}'")
    depth_weight_factor = 1.0 / current_depth  # 随着深度增加，权重递减
    
    try:
        # 获取用户的关注者
        followers_url = f"https://api.github.com/users/{username}/followers"
        followers_response = requests.get(followers_url, headers=headers, timeout=10)
        
        if followers_response.status_code != 200:
            logger.warning(f"请求用户 '{username}' 的关注者失败，状态码: {followers_response.status_code}")
            return
            
        followers = followers_response.json()
        logger.info(f"获取到用户 '{username}' 的关注者: {len(followers)} 人")
        
        # 分析关注者和被关注者的位置，加权处理
        mutual_followers = []  # 存储互相关注的用户
        
        for follower in followers[:min(20, len(followers))]:  # 限制每层处理的关注者数量
            try:
                follower_name = follower['login']
                
                if follower_name in processed_users:
                    logger.info(f"用户 '{follower_name}' 已处理过，跳过")
                    continue
                    
                processed_users.add(follower_name)
                
                # 检查是否互相关注
                following_url = f"https://api.github.com/users/{follower_name}/following/{username}"
                following_response = requests.get(following_url, headers=headers, timeout=10)
                
                is_mutual = following_response.status_code == 204
                base_weight = 2.0 if is_mutual else 1.0  # 互相关注的基础权重更高
                weight = base_weight * depth_weight_factor  # 根据深度调整权重
                
                # 获取关注者的位置
                follower_profile_url = f"https://api.github.com/users/{follower_name}"
                follower_profile_response = requests.get(follower_profile_url, headers=headers, timeout=10)
                
                if follower_profile_response.status_code == 200:
                    follower_data = follower_profile_response.json()
                    location = follower_data.get("location")
                    bio = follower_data.get("bio", "")
                    
                    # 处理位置信息
                    if location and not any(char in location for char in ['#', '%', '&', '*', '乱码']):
                        logger.info(f"关注者 '{follower_name}' 的位置: {location}, 深度: {current_depth}, 权重: {weight:.2f}")
                        if location in location_weights:
                            location_weights[location] += weight
                        else:
                            location_weights[location] = weight
                    
                    # 分析简介中可能包含的位置信息
                    if bio and len(bio) > 5:
                        bio_weight = weight * 0.5  # 简介信息的权重较低
                        logger.info(f"分析关注者 '{follower_name}' 的简介信息")
                        
                        # 简单的位置关键词检测
                        location_keywords = {
                            "China": "CN", "中国": "CN", "Beijing": "CN", "Shanghai": "CN", "Shenzhen": "CN",
                            "USA": "US", "United States": "US", "America": "US", "New York": "US", "California": "US",
                            "Japan": "JP", "Tokyo": "JP", "日本": "JP",
                            "Korea": "KR", "韩国": "KR", "Seoul": "KR",
                            "India": "IN", "Mumbai": "IN", "Delhi": "IN",
                            "UK": "GB", "United Kingdom": "GB", "London": "GB", "England": "GB",
                            "Germany": "DE", "Berlin": "DE", "德国": "DE",
                            "France": "FR", "Paris": "FR", "法国": "FR",
                            "Russia": "RU", "Moscow": "RU", "俄罗斯": "RU",
                            "Canada": "CA", "Toronto": "CA", "Vancouver": "CA",
                            "Australia": "AU", "Sydney": "AU", "Melbourne": "AU"
                        }
                        
                        for keyword, country_code in location_keywords.items():
                            if keyword.lower() in bio.lower():
                                logger.info(f"在关注者 '{follower_name}' 的简介中发现位置关键词: {keyword} -> {country_code}")
                                location_name = f"bio:{country_code}"
                                if location_name in location_weights:
                                    location_weights[location_name] += bio_weight
                                else:
                                    location_weights[location_name] = bio_weight
                                break
                
                # 如果是互相关注，记录下来进行下一层递归分析
                if is_mutual and current_depth < max_depth:
                    mutual_followers.append(follower_name)
                    
            except Exception as e:
                logger.warning(f"处理关注者 '{follower_name}' 时发生错误: {str(e)}")
                continue
        
        # 对互相关注的用户进行下一层级分析
        for mutual_follower in mutual_followers[:min(5, len(mutual_followers))]:  # 限制递归分析的用户数量
            _analyze_network_level(mutual_follower, location_weights, processed_users, 
                                  current_depth + 1, max_depth, logger)
                
    except requests.exceptions.RequestException as e:
        logger.error(f"分析用户 '{username}' 的社交网络层级 {current_depth} 时发生网络错误: {str(e)}")
    except Exception as e:
        logger.error(f"分析用户 '{username}' 的社交网络层级 {current_depth} 时发生错误: {str(e)}")
