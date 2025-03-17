from collections import Counter
import logging
import time
import requests
from config import headers
import re

def analyze_commit_timezone(username, limit=100):
    """分析用户提交记录中的时区信息推测所在国家"""
    logger = logging.getLogger(__name__)
    logger.info(f"开始分析用户 '{username}' 的提交时区信息")
    
    timezone_counter = Counter()
    
    try:
        # 获取用户的仓库
        repos_url = f"https://api.github.com/users/{username}/repos"
        repos_response = requests.get(repos_url, headers=headers, timeout=10)
        
        if repos_response.status_code != 200:
            logger.warning(f"请求用户 '{username}' 仓库列表失败，状态码: {repos_response.status_code}")
            return None
        
        repos = repos_response.json()
        commits_analyzed = 0
        
        for repo in repos:
            if commits_analyzed >= limit:
                break
                
            repo_name = repo["name"]
            try:
                commits_url = f"https://api.github.com/repos/{username}/{repo_name}/commits?author={username}"
                commits_response = requests.get(commits_url, headers=headers, timeout=10)
                
                if commits_response.status_code != 200:
                    logger.warning(f"请求用户 '{username}' 仓库 '{repo_name}' 的提交记录失败，状态码: {commits_response.status_code}")
                    continue
                    
                commits = commits_response.json()
                
                for commit in commits:
                    if "commit" in commit and "author" in commit["commit"]:
                        date_str = commit["commit"]["author"].get("date")
                        if date_str:
                            try:
                                # 尝试从ISO格式提取标准时区信息
                                # 例如 "2023-01-01T12:00:00+08:00" 或 "2023-01-01T12:00:00Z"
                                if date_str.endswith('Z'):
                                    # UTC时间，标准化为 "+0000"
                                    timezone = "+0000"
                                    logger.debug(f"检测到UTC时间标记 'Z'，标准化为 '+0000'")
                                else:
                                    # 提取 +08:00 或 -05:00 格式的时区
                                    timezone_match = re.search(r'([+-]\d{2}):?(\d{2})$', date_str)
                                    if timezone_match:
                                        hours, minutes = timezone_match.groups()
                                        # 标准化为 +0800 或 -0500 格式
                                        timezone = f"{hours}{minutes}"
                                        logger.debug(f"从日期 '{date_str}' 提取时区: {timezone}")
                                    else:
                                        # 如果无法提取标准时区，尝试其他格式
                                        # 例如一些非标准格式如 "12:42Z"
                                        non_standard_match = re.search(r'(\d{2}):(\d{2})Z', date_str)
                                        if non_standard_match:
                                            hours, minutes = non_standard_match.groups()
                                            # 将非标准格式转换为标准UTC偏移
                                            timezone = "+0000"  # 假设Z表示UTC
                                            logger.debug(f"检测到非标准时区格式 '{date_str}'，标准化为 '+0000'")
                                        else:
                                            logger.warning(f"无法从日期 '{date_str}' 提取时区信息")
                                            continue
                                
                                timezone_counter[timezone] += 1
                                commits_analyzed += 1
                            except Exception as e:
                                logger.warning(f"解析日期 '{date_str}' 时发生错误: {str(e)}")
                                continue
                                
                    if commits_analyzed >= limit:
                        break
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求用户 '{username}' 仓库 '{repo_name}' 的提交记录时发生网络错误: {str(e)}")
                continue
            except Exception as e:
                logger.warning(f"处理用户 '{username}' 仓库 '{repo_name}' 的提交记录时发生错误: {str(e)}")
                continue
        
        # 返回最常用的时区
        result = timezone_counter.most_common(3) if timezone_counter else None
        logger.info(f"完成用户 '{username}' 的提交时区分析，找到 {len(timezone_counter)} 个不同时区")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"分析用户 '{username}' 的提交时区时发生网络错误: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"分析用户 '{username}' 的提交时区时发生错误: {str(e)}")
        return None


def analyze_activity_patterns(username, days=30):
    """分析用户活动时间模式推测时区和国家"""
    logger = logging.getLogger(__name__)
    logger.info(f"开始分析用户 '{username}' 的活动模式")
    
    activity_hours = [0] * 24  # 24小时活动分布
    activity_days = [0] * 7    # 一周7天的活动分布
    activity_dates = {}        # 记录具体日期的活动
    
    try:
        events_url = f"https://api.github.com/users/{username}/events"
        response = requests.get(events_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.warning(f"请求用户 '{username}' 活动失败，状态码: {response.status_code}")
            return None
            
        events = response.json()
        logger.info(f"获取到用户 '{username}' 的活动事件: {len(events)} 个")
        
        for event in events:
            created_at = event.get("created_at")
            if created_at:
                try:
                    # 解析ISO时间格式
                    event_time = time.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                    
                    # 记录小时分布（UTC时间）
                    hour = event_time.tm_hour
                    activity_hours[hour] += 1
                    
                    # 记录星期几分布
                    weekday = event_time.tm_wday  # 0-6，0是周一
                    activity_days[weekday] += 1
                    
                    # 记录具体日期
                    date_str = time.strftime("%Y-%m-%d", event_time)
                    if date_str in activity_dates:
                        activity_dates[date_str] += 1
                    else:
                        activity_dates[date_str] = 1
                        
                except ValueError as e:
                    logger.warning(f"解析用户 '{username}' 活动时间失败: {str(e)}")
                    continue
                except Exception as e:
                    logger.warning(f"处理用户 '{username}' 活动时间时发生错误: {str(e)}")
                    continue
                    
        # 如果没有活动数据，返回None
        if sum(activity_hours) == 0:
            logger.info(f"用户 '{username}' 没有活动数据")
            return None
            
        # 分析活动高峰
        max_activity_hour = activity_hours.index(max(activity_hours))
        
        # 查找连续3小时的活动高峰期
        rolling_sum = []
        for i in range(24):
            # 计算连续3小时的活动总和（环形数组，处理跨日情况）
            three_hour_sum = sum(activity_hours[(i + j) % 24] for j in range(3))
            rolling_sum.append((i, three_hour_sum))
        
        # 找出活动最集中的3小时时段
        peak_period_start, _ = max(rolling_sum, key=lambda x: x[1])
        peak_period = [(peak_period_start + i) % 24 for i in range(3)]
        
        # 推测时区 - 假设用户主要在当地时间9:00-18:00活动
        # 工作时间中点约为13点，如果活动高峰在UTC的3点，则时区可能是UTC+10
        work_mid_hour = 13  # 工作日中间时间点
        estimated_timezone = (peak_period_start + 1 - work_mid_hour) % 24  # 取3小时中间点
        if estimated_timezone > 12:  # 处理负时区
            estimated_timezone -= 24
            
        # 格式化时区字符串
        timezone_str = f"+{estimated_timezone:02d}00" if estimated_timezone >= 0 else f"{estimated_timezone:03d}00"
        
        # 检查周末活动模式
        weekday_activity = sum(activity_days[:5])  # 周一至周五
        weekend_activity = sum(activity_days[5:])  # 周六和周日
        weekend_ratio = weekend_activity / (weekday_activity + weekend_activity) if (weekday_activity + weekend_activity) > 0 else 0
        
        result = {
            "activity_hours": activity_hours,
            "activity_days": activity_days,
            "peak_hour_utc": max_activity_hour,
            "peak_period_utc": peak_period,
            "estimated_timezone": timezone_str,
            "weekend_ratio": weekend_ratio,
            "total_events": len(events),
            "active_dates": len(activity_dates)
        }
        
        logger.info(f"完成用户 '{username}' 的活动模式分析，活动高峰时间(UTC): {max_activity_hour}点，估计时区: {timezone_str}")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"分析用户 '{username}' 的活动模式时发生网络错误: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"分析用户 '{username}' 的活动模式时发生错误: {str(e)}")
        return None
