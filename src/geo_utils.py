import logging


def geocode_location(location_str):
    """将位置字符串解析为标准国家/地区代码"""
    logger = logging.getLogger(__name__)
    
    if not location_str:
        logger.info("位置字符串为空")
        return None
        
    # 转为小写并清理
    location_clean = location_str.lower().strip()
    logger.info(f"正在解析位置字符串: '{location_clean}'")
    
    # 创建一个更全面的地区映射字典
    country_mapping = {
        # 中国相关
        'china': 'CN', 'prc': 'CN', '中国': 'CN', 'beijing': 'CN', 'shanghai': 'CN', 
        'guangzhou': 'CN', 'shenzhen': 'CN', 'hangzhou': 'CN', 'nanjing': 'CN',
        'chengdu': 'CN', 'wuhan': 'CN', 'tianjin': 'CN', 'chongqing': 'CN',
        'xi\'an': 'CN', 'xian': 'CN', 'suzhou': 'CN', 'dalian': 'CN',
        
        # 美国相关
        'usa': 'US', 'us': 'US', 'united states': 'US', '美国': 'US', 
        'california': 'US', 'san francisco': 'US', 'new york': 'US',
        'seattle': 'US', 'boston': 'US', 'chicago': 'US', 'los angeles': 'US',
        'la': 'US', 'sf': 'US', 'nyc': 'US', 'washington': 'US', 'dc': 'US',
        'texas': 'US', 'austin': 'US', 'dallas': 'US', 'houston': 'US',
        'florida': 'US', 'miami': 'US', 'atlanta': 'US', 'georgia': 'US',
        
        # 日本相关
        'japan': 'JP', '日本': 'JP', 'tokyo': 'JP', 'osaka': 'JP', 'kyoto': 'JP',
        
        # 韩国相关
        'korea': 'KR', 'south korea': 'KR', '韩国': 'KR', 'seoul': 'KR', 'busan': 'KR',
        
        # 印度相关
        'india': 'IN', '印度': 'IN', 'bangalore': 'IN', 'mumbai': 'IN', 'delhi': 'IN',
        'hyderabad': 'IN', 'chennai': 'IN',
        
        # 英国相关
        'uk': 'GB', 'united kingdom': 'GB', 'england': 'GB', 'britain': 'GB',
        '英国': 'GB', 'london': 'GB', 'manchester': 'GB', 'liverpool': 'GB',
        
        # 加拿大相关
        'canada': 'CA', '加拿大': 'CA', 'toronto': 'CA', 'vancouver': 'CA', 'montreal': 'CA',
        
        # 澳大利亚相关
        'australia': 'AU', '澳大利亚': 'AU', 'sydney': 'AU', 'melbourne': 'AU', 'brisbane': 'AU',
        
        # 德国相关
        'germany': 'DE', '德国': 'DE', 'berlin': 'DE', 'munich': 'DE', 'hamburg': 'DE',
        
        # 法国相关
        'france': 'FR', '法国': 'FR', 'paris': 'FR', 'lyon': 'FR', 'marseille': 'FR',
        
        # 俄罗斯相关
        'russia': 'RU', '俄罗斯': 'RU', 'moscow': 'RU', 'saint petersburg': 'RU',
        
        # 巴西相关
        'brazil': 'BR', '巴西': 'BR', 'sao paulo': 'BR', 'rio de janeiro': 'BR',
        
        # 新加坡
        'singapore': 'SG', '新加坡': 'SG',
        
        # 荷兰
        'netherlands': 'NL', 'holland': 'NL', '荷兰': 'NL', 'amsterdam': 'NL',
        
        # 瑞典
        'sweden': 'SE', '瑞典': 'SE', 'stockholm': 'SE',
        
        # 瑞士
        'switzerland': 'CH', '瑞士': 'CH', 'zurich': 'CH', 'geneva': 'CH',
        
        # 西班牙
        'spain': 'ES', '西班牙': 'ES', 'madrid': 'ES', 'barcelona': 'ES',
        
        # 意大利
        'italy': 'IT', '意大利': 'IT', 'rome': 'IT', 'milan': 'IT',
    }
    
    # 直接匹配
    if location_clean in country_mapping:
        result = country_mapping[location_clean]
        logger.info(f"位置 '{location_clean}' 直接匹配到国家代码: {result}")
        return result
        
    # 部分匹配
    for key, value in country_mapping.items():
        if key in location_clean:
            logger.info(f"位置 '{location_clean}' 部分匹配到关键词 '{key}'，国家代码: {value}")
            return value
            
    logger.info(f"无法解析位置 '{location_clean}' 到任何已知国家")
    return None

def get_country_name(country_code):
    """
    将国家代码转换为国家名称
    """
    country_map = {
        "CN": "中国",
        "US": "美国",
        "JP": "日本",
        "KR": "韩国",
        "IN": "印度",
        "GB": "英国",
        "CA": "加拿大",
        "AU": "澳大利亚",
        "DE": "德国",
        "FR": "法国",
        "RU": "俄罗斯",
        "BR": "巴西",
        "SG": "新加坡",
        "NL": "荷兰",
        "SE": "瑞典",
        "CH": "瑞士",
        "ES": "西班牙",
        "IT": "意大利",
        "IL": "以色列",
        "FI": "芬兰",
        "NO": "挪威",
        "DK": "丹麦",
        "BE": "比利时",
        "AT": "奥地利",
        "PT": "葡萄牙",
        "IE": "爱尔兰",
        "NZ": "新西兰",
        "ZA": "南非",
        "MX": "墨西哥",
        "AR": "阿根廷",
        "TH": "泰国",
        "VN": "越南",
        "MY": "马来西亚",
        "ID": "印度尼西亚",
        "PH": "菲律宾",
        "TR": "土耳其",
        "SA": "沙特阿拉伯",
        "AE": "阿联酋",
        "IR": "伊朗",
        "PK": "巴基斯坦",
        "BD": "孟加拉国",
        "EG": "埃及",
        "NG": "尼日利亚",
        "UA": "乌克兰",
        "PL": "波兰",
        "RO": "罗马尼亚",
        "CZ": "捷克",
        "HU": "匈牙利",
        "GR": "希腊",
        "IS": "冰岛",
        "FJ": "斐济",
        "NC": "新喀里多尼亚",
        "CV": "佛得角",
        "GS": "南乔治亚岛",
        "UY": "乌拉圭",
        "MM": "缅甸",
        "NP": "尼泊尔",
        "AF": "阿富汗",
        "GH": "加纳",
        "BG": "保加利亚"
    }
    
    return country_map.get(country_code, f"未知({country_code})")
