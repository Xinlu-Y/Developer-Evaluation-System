from collections import Counter
import logging

import requests
from config import headers
 
def get_user_profile(username):
    """
    获取用户的个人资料信息
    """
    logger = logging.getLogger(__name__)
    logger.info(f"正在获取用户 '{username}' 的个人资料")

    url = f"https://api.github.com/users/{username}"
    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.warning(f"请求用户资料失败，状态码: {response.status_code}, 用户名: '{username}'")
            logger.debug(f"响应内容: {response.json()}")
            return None

        profile_data = response.json()
        profile = {
            "用户名": profile_data.get("login"),
            "全名": profile_data.get("name"),
            "公司": profile_data.get("company"),
            "博客": profile_data.get("blog"),
            "国家": profile_data.get("location"),
            "邮箱": profile_data.get("email"),
            "简介": profile_data.get("bio"),
            "公开仓库数": profile_data.get("public_repos"),
            "关注者数": profile_data.get("followers"),
            "关注中": profile_data.get("following"),
            "GitHub 个人主页": profile_data.get("html_url")
        }
        logger.info(f"成功获取用户 '{username}' 的个人资料")
        return profile
    except requests.exceptions.RequestException as e:
        logger.error(f"请求用户 '{username}' 资料时发生网络错误: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"获取用户 '{username}' 资料时发生错误: {str(e)}")
        return None    


def get_user_total_stars(username):
    """
    获取用户的所有仓库的总 Star 数（包括用户作为 Owner 和 Member 的仓库）。
    """

    total_stars = 0

    # 遍历仓库类型（Owner 和 Member）
    for repo_type in ["owner", "member"]:
        page = 1
        while True:
            url = f"https://api.github.com/users/{username}/repos?page={page}&per_page=100&type={repo_type}"
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                print(f"请求 {repo_type} 仓库失败，状态码: {response.status_code}")
                break

            data = response.json()
            if not data:
                break

            # 累加每个仓库的 star 数
            for repo in data:
                total_stars += repo.get("stargazers_count", 0)

            page += 1

    return total_stars


def get_user_repos(username):
    """
    获取用户的仓库信息（包括用户作为 Owner 和 Member 的仓库），并统计总的 Star 数和 Fork 数
    """

    repos = []
    total_stars = 0
    total_forks = 0

    # 遍历仓库类型（Owner 和 Member）
    for repo_type in ["owner", "member"]:
        page = 1
        while True:
            url = f"https://api.github.com/users/{username}/repos?page={page}&per_page=100&type={repo_type}"
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                print(f"请求 {repo_type} 仓库失败，状态码: {response.status_code}")
                break

            data = response.json()
            if not data:
                break

            for repo in data:
                star_count = repo.get("stargazers_count", 0)
                fork_count = repo.get("forks_count", 0)
                total_stars += star_count
                total_forks += fork_count
                langs_url = repo.get("languages_url")
                languages = []
                langs_resp = requests.get(langs_url, headers=headers)
                if langs_resp.status_code == 200:
                    langs_json = langs_resp.json()
                    languages = list(langs_json.keys())
                repos.append({
                    "repo_name": repo.get("name"),
                    "repo_description": repo.get("description"),
                    "Star": star_count,
                    "Fork": fork_count,
                    "repo_type": repo_type,
                    "html_url": repo.get("html_url", ""),
                    "repo_topics": repo.get("topics", []),
                    "repo_languages": languages
                })

            page += 1

    return repos


def get_all_users(url):
    """ 通过分页获取 GitHub API 返回的所有用户数据 """
    users = []
    page = 1
    while True:
        paginated_url = f"{url}?page={page}&per_page=100"
        response = requests.get(paginated_url, headers=headers)

        if response.status_code != 200:
            break

        data = response.json()
        if not data:
            break  # 数据为空，说明已获取完所有用户

        users.extend(data)
        page += 1  # 进入下一页

    return users


def get_user_mutual_followers(username):
    """ 获取某个 GitHub 用户的互相关注列表 """
    followers_url = f"https://api.github.com/users/{username}/followers"
    following_url = f"https://api.github.com/users/{username}/following"

    followers = get_all_users(followers_url)  # 获取所有关注者
    following = get_all_users(following_url)  # 获取所有关注的人

    # 将 followers 和 following 的 login 名称存入集合，方便快速查找
    followers_set = {user['login'] for user in followers}
    following_set = {user['login'] for user in following}

    # 计算交集，得到互相关注者
    if len(followers) <= len(following):
      following_set = {user['login'] for user in following}
      mutual_followers = [user['login'] for user in followers if user['login'] in following_set]
    else:
      followers_set = {user['login'] for user in followers}
      mutual_followers = [user['login'] for user in following if user['login'] in followers_set]

    return mutual_followers


# TODO: 可以修改成根据分析相互关注者来推测用户国家
def get_user_profile_nation_detect(username):
    """
    获取用户的个人资料信息，并分别获取关注者和关注中的人的国家信息，更新用户国家信息
    """
    # 获取用户的个人资料
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"请求用户资料失败，状态码: {response.status_code}")
        return None

    profile_data = response.json()
    location = profile_data.get("location")

    # 清洗用户的国家信息
    if not location or any(char in location for char in ['#', '%', '&', '*', '乱码']):
        location = "Unknown"

    profile = {
        "用户名": profile_data.get("login"),
        "全名": profile_data.get("name"),
        "公司": profile_data.get("company"),
        "博客": profile_data.get("blog"),
        "国家": location,  # 使用清洗后的国家信息
        "邮箱": profile_data.get("email"),
        "简介": profile_data.get("bio"),
        "公开仓库数": profile_data.get("public_repos"),
        "关注者数": profile_data.get("followers"),
        "关注中": profile_data.get("following"),
        "GitHub 个人主页": profile_data.get("html_url")
    }

    if location == "Unknown":
        # 获取互相关注用户的国家信息
        mutual_follow_nations = []
        mutual_followers = get_user_mutual_followers(username)

        for follower_name in mutual_followers:
            follower_profile_url = f"https://api.github.com/users/{follower_name}"
            follower_profile_response = requests.get(follower_profile_url, headers=headers)

            if follower_profile_response.status_code == 200:
                follower_data = follower_profile_response.json()
                follower_location = follower_data.get("location")
                if follower_location and not any(
                        char in follower_location for char in ['#', '%', '&', '*', '乱码']):
                    mutual_follow_nations.append(follower_location)

        # 获取"关注中"用户的国家信息
        following_nations = []
        following_users = get_all_users(f"https://api.github.com/users/{username}/following")

        for user in following_users:
            user_url = user.get("url")  # 获取每个用户的详细资料 URL
            user_response = requests.get(user_url, headers=headers)
            if user_response.status_code == 200:
                user_data = user_response.json()
                user_location = user_data.get("location")
                if user_location and not any(char in user_location for char in ['#', '%', '&', '*', '乱码']):
                    following_nations.append(user_location)

        # 统计出现最多的国家
        most_common_follower_nation = Counter(mutual_follow_nations).most_common(1)[0][0] if mutual_follow_nations else None
        most_common_following_nation = Counter(following_nations).most_common(1)[0][0] if following_nations else None

        # 更新用户国家信息
        if most_common_follower_nation and most_common_following_nation:
            if most_common_follower_nation == most_common_following_nation:
                location = most_common_follower_nation
            else:
                location = most_common_following_nation
        elif most_common_following_nation:
            location = most_common_following_nation
        elif most_common_follower_nation:
            location = most_common_follower_nation

        profile["国家"] = location
        profile["关注者出现最多的国家"] = most_common_follower_nation
        profile["关注中出现最多的国家"] = most_common_following_nation

    return profile

            

