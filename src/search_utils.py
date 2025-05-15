import logging
import time
import requests
from config import headers

def search_repositories_by_language_and_topic(language, topic, max_results):
    """
    使用 GitHub 搜索 API 组合搜索项目，按编程语言和主题标签筛选，
    并只返回个人用户创建的项目。分页获取最多 max_results 条结果。
    """
    logger = logging.getLogger(__name__)
    
    # 每页获取 30 个结果（GitHub API 默认值）
    per_page = 30
    pages = (max_results // per_page) + (1 if max_results % per_page > 0 else 0)
    
    # 创建一个空列表来存储所有符合条件的个人用户项目的信息
    profiles = []
    max_retries = 3
    retry_delay = 5
    
    for page in range(1, pages + 1):
        retries = 0
        while retries < max_retries:
            try:
                # 构建搜索查询
                query = f"language:{language}+topic:{topic}"
                url = f"https://api.github.com/search/repositories?q={query}&per_page={per_page}&page={page}"
                
                logger.info(f"正在请求第 {page} 页，URL: {url}")
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    repositories = response.json().get('items', [])
                    logger.info(f"成功获取第 {page} 页，找到 {len(repositories)} 个仓库")
                    
                    for repo in repositories:
                        # 筛选出个人用户创建的项目
                        if repo['owner'].get("type") == "User":
                            profiles.append(repo['owner'].get("login"))
                            
                            # 如果达到了 max_results，停止添加
                            if len(profiles) >= max_results:
                                break
                    # 如果达到了 max_results，停止分页
                    if len(profiles) >= max_results:
                        break
                    break  # 成功获取数据，跳出重试循环
                    
                elif response.status_code == 403:
                    logger.error("GitHub API 速率限制已达到，等待重试")
                    time.sleep(60)  # 如果达到速率限制，等待60秒
                    retries += 1
                    
                elif response.status_code == 401:
                    logger.error("GitHub Token 无效或未设置")
                    return []
                    
                else:
                    logger.error(f"请求失败，状态码: {response.status_code}")
                    retries += 1
                    time.sleep(retry_delay)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {str(e)}")
                retries += 1
                time.sleep(retry_delay)
                
        if retries == max_retries:
            logger.error(f"第 {page} 页请求失败，已达到最大重试次数")
            break
            
    logger.info(f"搜索完成，共找到 {len(profiles)} 个开发者")
    return profiles[:max_results]  # 确保只返回需要的数量
