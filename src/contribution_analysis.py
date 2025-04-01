import requests
from config import headers

def calculate_contribution_score(events):
    """
    根据用户的活动事件计算贡献分数，返回每个仓库的贡献分数和贡献评价。
    """
    weights = {
        "PushEvent": 0.4,
        "PullRequestEvent": 0.3,
        "IssuesEvent": 0.2,
        "ForkEvent": 0.05,
        "WatchEvent": 0.05
    }
    contribution_score = {}

    for event in events:
        repo_name = event["repo"]["name"]
        event_type = event["type"]

        # 初始化项目的贡献分数
        if repo_name not in contribution_score:
            contribution_score[repo_name] = 0

        # 更新贡献分数
        if event_type in weights:
            # 如果是 PullRequestEvent 并且未合并，权重减半
            if event_type == "PullRequestEvent" and not event.get("payload", {}).get("pull_request", {}).get("merged",
                                                                                                             False):
                contribution_score[repo_name] += weights[event_type] / 2
            else:
                contribution_score[repo_name] += weights[event_type]

    # 为没有事件记录的仓库分配最低贡献度
    for repo in contribution_score:
        if contribution_score[repo] == 0:
            contribution_score[repo] = 0.1  # 最低贡献分数

    # 根据贡献分数返回贡献度评价
    contribution_evaluation = {}
    for repo, score in contribution_score.items():
        if score >= 1.5:
            evaluation = 3
        elif score >= 0.5:
            evaluation = 2
        else:
            evaluation = 1
        contribution_evaluation[repo] = evaluation

    return contribution_evaluation


def evaluate_combined_influence(repo_star, repo_fork):
    """
    根据仓库的 star 数和 fork 数计算贡献项目的影响力
    """
    influence_score = repo_star * 0.7 + repo_fork * 0.3
    if influence_score >= 1000:
        return 5
    elif influence_score >= 500:
        return 4
    elif influence_score >= 100:
        return 3
    elif influence_score >= 10:
        return 2
    else:
        return 1


def evaluate_overall_contribution(contributed_repos):
    """
    根据仓库的影响力和贡献分数对用户的总体贡献进行评价。
    """
    total_score = 0
    total_weight = 0

    # 遍历所有仓库，计算加权贡献分数
    for repo in contributed_repos:
        repo_influence_score = repo["repo_influence"]
        contribution_score = repo["contribution"]

        # 设定权重：假设影响力和贡献度各占一半
        weighted_score = (repo_influence_score * 0.5) + (contribution_score * 0.5)
        total_score += weighted_score
        total_weight += 1

    # 计算平均贡献分数
    # average_score = total_score / total_weight if total_weight > 0 else 0

    return total_score


def get_user_contributed_repos(username):
    """
    获取用户每个贡献过的仓库的资料，包括仓库的名称、star 数、仓库地址和贡献分数。
    """

    contributed_repos = []  # 存储符合条件的仓库信息
    page = 1

    while True:
        url = f"https://api.github.com/users/{username}/events?page={page}&per_page=100"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"请求用户活动失败，状态码: {response.status_code}")
            break

        events = response.json()
        if not events:
            break

        # 计算贡献分数
        contribution_scores = calculate_contribution_score(events)

        # 遍历用户的活动，统计每个仓库的事件
        for event in events:
            repo_name = event["repo"]["name"]  # 获取仓库名称

            # 检查是否已记录该仓库
            if not any(repo["repo_name"] == repo_name for repo in contributed_repos):
                # 获取仓库的 star 数和 URL
                repo_url = f"https://api.github.com/repos/{repo_name}"
                repo_response = requests.get(repo_url, headers=headers)
                if repo_response.status_code == 200:
                    repo_data = repo_response.json()
                    repo_star = repo_data.get("stargazers_count", 0)
                    repo_fork = repo_data.get("forks_count", 0)

                    contributed_repos.append({
                        "repo_name": repo_name,
                        "repo_star": repo_star,
                        "repo_influence": evaluate_combined_influence(repo_star, repo_fork),
                        "repo_url": repo_data.get("html_url", ""),
                        "contribution": contribution_scores.get(repo_name, 0)
                    })
                else:
                    print(f"请求仓库详情失败，状态码: {repo_response.status_code}，仓库: {repo_name}")

        page += 1

    return contributed_repos

def calculate_talent_rank(total_stars, followers, contribution_score):
    # 定义权重
    total_stars_weight = 0.4
    followers_weight = 0.3
    contribution_score_weight = 0.3

    # 计算 TalentRank_score
    TalentRank_score = (
            total_stars * total_stars_weight +
            followers * followers_weight +
            contribution_score * contribution_score_weight
    )
    return int(TalentRank_score)

