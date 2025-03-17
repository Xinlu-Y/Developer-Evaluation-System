import logging
import requests
from config import headers
from contribution_analysis import get_user_contributed_repos

def analyze_social_network(username, depth=2):
    """深入分析用户的社交网络，包括合作者和共同关注者"""
    logger = logging.getLogger(__name__)
    logger.info(f"开始分析用户 '{username}' 的社交网络")
    
    location_weights = {}
    
    try:
        # 获取用户的关注者
        followers_url = f"https://api.github.com/users/{username}/followers"
        followers_response = requests.get(followers_url, headers=headers, timeout=10)
        
        if followers_response.status_code != 200:
            logger.warning(f"请求用户 '{username}' 的关注者失败，状态码: {followers_response.status_code}")
            return None
            
        followers = followers_response.json()
        logger.info(f"获取到用户 '{username}' 的关注者: {len(followers)} 人")
        
        # 分析关注者和被关注者的位置，加权处理
        for follower in followers:
            try:
                follower_name = follower['login']
                
                # 检查是否互相关注
                following_url = f"https://api.github.com/users/{follower_name}/following/{username}"
                following_response = requests.get(following_url, headers=headers, timeout=10)
                
                is_mutual = following_response.status_code == 204
                weight = 2.0 if is_mutual else 1.0  # 互相关注的权重更高
                
                # 获取关注者的位置
                follower_profile_url = f"https://api.github.com/users/{follower_name}"
                follower_profile_response = requests.get(follower_profile_url, headers=headers, timeout=10)
                
                if follower_profile_response.status_code == 200:
                    follower_data = follower_profile_response.json()
                    location = follower_data.get("location")
                    
                    if location and not any(char in location for char in ['#', '%', '&', '*', '乱码']):
                        logger.info(f"关注者 '{follower_name}' 的位置: {location}, 权重: {weight}")
                        if location in location_weights:
                            location_weights[location] += weight
                        else:
                            location_weights[location] = weight
            except Exception as e:
                logger.warning(f"处理关注者 '{follower_name}' 时发生错误: {str(e)}")
                continue
                    
        # 获取共同贡献者信息
        try:
            contributed_repos = get_user_contributed_repos(username)
            logger.info(f"获取到用户 '{username}' 的贡献仓库: {len(contributed_repos)} 个")
            
            for repo_info in contributed_repos:
                try:
                    repo_name = repo_info["repo_name"]
                    contributors_url = f"https://api.github.com/repos/{repo_name}/contributors"
                    contributors_response = requests.get(contributors_url, headers=headers, timeout=10)
                    
                    if contributors_response.status_code != 200:
                        logger.warning(f"请求仓库 '{repo_name}' 的贡献者失败，状态码: {contributors_response.status_code}")
                        continue
                        
                    contributors = contributors_response.json()
                    
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
            logger.warning(f"获取用户 '{username}' 的贡献仓库时发生错误: {str(e)}")
        
        # 返回按权重排序的位置列表
        result = sorted(location_weights.items(), key=lambda x: x[1], reverse=True)
        logger.info(f"完成用户 '{username}' 的社交网络分析，找到 {len(location_weights)} 个不同位置")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"分析用户 '{username}' 的社交网络时发生网络错误: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"分析用户 '{username}' 的社交网络时发生错误: {str(e)}")
        return None
