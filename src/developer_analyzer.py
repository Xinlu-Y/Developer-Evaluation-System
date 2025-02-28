import requests
import os
import logging

# 配置 GitHub Token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"token {GITHUB_TOKEN}"}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('github_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_user_profile(username):
    """
    获取用户的个人资料信息
    """
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logger.error(f"请求用户资料失败，状态码: {response.status_code}")
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
    
    return profile


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

                repos.append({
                    "repo_name": repo.get("name"),
                    "repo_description": repo.get("description"),
                    "Star": star_count,
                    "Fork": fork_count,
                    "repo_type": repo_type
                })

            page += 1

    # 将仓库信息转换为 DataFrame
    # df_repos = pd.DataFrame(repos)

    return repos


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

        # 获取关注者列表
        followers_url = f"https://api.github.com/users/{username}/followers"
        followers_response = requests.get(followers_url, headers=headers)
        if followers_response.status_code == 200:
            followers = followers_response.json()

            for follower in followers:
                follower_name = follower['login']
                # 检查互相关注
                following_url = f"https://api.github.com/users/{follower_name}/following/{username}"
                following_response = requests.get(following_url, headers=headers)

                if following_response.status_code == 204:  # 如果互相关注
                    # 获取该互相关注者的位置信息
                    follower_profile_url = f"https://api.github.com/users/{follower_name}"
                    follower_profile_response = requests.get(follower_profile_url, headers=headers)
                    if follower_profile_response.status_code == 200:
                        follower_data = follower_profile_response.json()
                        follower_location = follower_data.get("location")
                        # 清洗并记录互相关注者的有效国家信息
                        if follower_location and not any(
                                char in follower_location for char in ['#', '%', '&', '*', '乱码']):
                            mutual_follow_nations.append(follower_location)

        # 获取"关注中"用户的国家信息
        following_nations = []
        following_url = f"https://api.github.com/users/{username}/following"
        following_response = requests.get(following_url, headers=headers)
        if following_response.status_code == 200:
            following = following_response.json()
            for user in following:
                user_url = user.get("url")  # 获取每个用户的详细资料 URL
                user_response = requests.get(user_url, headers=headers)
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    user_location = user_data.get("location")
                    # 仅在 user_location 有效时添加
                    if user_location and not any(char in user_location for char in ['#', '%', '&', '*', '乱码']):
                        following_nations.append(user_location)

        # 统计出现最多的国家
        most_common_follower_nation = Counter(mutual_follow_nations).most_common(1)[0][
            0] if mutual_follow_nations else None
        most_common_following_nation = Counter(following_nations).most_common(1)[0][0] if following_nations else None

        # 更新用户国家信息
        if most_common_follower_nation and most_common_following_nation:
            if most_common_follower_nation == most_common_following_nation:
                location = most_common_follower_nation  # 两个国家相同，直接使用
            else:
                location = most_common_following_nation  # 不同则使用 "following" 出现最多的国家
        elif most_common_following_nation:
            location = most_common_following_nation
        elif most_common_follower_nation:
            location = most_common_follower_nation

        profile["国家"] = location
        profile["关注者出现最多的国家"] = most_common_follower_nation
        profile["关注中出现最多的国家"] = most_common_following_nation
        # print(mutual_follow_nations)

    # profile_df = pd.DataFrame([profile])
    return profile