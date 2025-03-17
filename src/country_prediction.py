import logging

from geo_utils import geocode_location
from language_culture import analyze_language_culture_hints
from social_network import analyze_social_network
from timezone_analysis import analyze_activity_patterns, analyze_commit_timezone
from user_profile import get_user_profile



def predict_country_with_confidence(username):
    """综合多种方法推测开发者所在国家，并提供置信度"""
    logger = logging.getLogger(__name__)
    logger.info(f"开始为用户 '{username}' 预测国家")
    
    evidence = {}
    confidence_scores = {}
    evidence_details = {}
    
    # 获取基本资料
    try:
        profile = get_user_profile(username)
        if profile and profile.get("国家") and profile.get("国家") != "Unknown":
            country = profile.get("国家")
            logger.info(f"用户 '{username}' 的个人资料中声明的国家/地区: {country}")
            geo_country = geocode_location(country)
            if geo_country:
                evidence["profile"] = geo_country
                # 提高个人资料的权重，因为这是用户自己提供的最直接信息
                confidence_scores["profile"] = 0.9  # 从0.8提高到0.9
                evidence_details["profile"] = {
                    "source": "个人资料",
                    "raw_value": country,
                    "mapped_value": geo_country,
                    "confidence": 0.9
                }
                logger.info(f"从个人资料中识别出国家代码: {geo_country}, 置信度: 0.9")
            else:
                logger.info(f"无法从个人资料中的位置 '{country}' 识别出国家代码")
        else:
            logger.info(f"用户 '{username}' 的个人资料中没有有效的国家/地区信息")
    except Exception as e:
        logger.warning(f"获取用户 '{username}' 的个人资料时发生错误: {str(e)}")
    
    # 分析提交时区
    try:
        timezone_data = analyze_commit_timezone(username)
        if timezone_data and len(timezone_data) > 0:
            most_common_tz = timezone_data[0][0]  # 最常用的时区
            tz_count = timezone_data[0][1]  # 该时区出现次数
            logger.info(f"用户 '{username}' 最常用的提交时区: {most_common_tz}, 次数: {tz_count}")
            
            # 扩展时区到国家的映射，增加更多可能性
            tz_country_map = {
                "+0800": {"CN": 0.7, "SG": 0.2, "MY": 0.1},  # 中国、新加坡、马来西亚等
                "+0900": {"JP": 0.7, "KR": 0.3},  # 日本、韩国
                "+0530": {"IN": 0.95},  # 印度
                "+0000": {"GB": 0.5, "PT": 0.2, "IS": 0.1, "GH": 0.1, "IE": 0.1},  # 英国、葡萄牙、冰岛、加纳、爱尔兰
                "-0400": {"US": 0.6, "CA": 0.3, "BR": 0.1},  # 美国东部、加拿大东部、巴西部分
                "-0500": {"US": 0.8, "CA": 0.2},  # 美国中部、加拿大部分
                "-0600": {"US": 0.8, "MX": 0.2},  # 美国山地时间、墨西哥
                "-0700": {"US": 0.9, "CA": 0.1},  # 美国太平洋时间、加拿大部分
                "-0800": {"US": 0.95},  # 美国阿拉斯加
                "+0100": {"DE": 0.3, "FR": 0.2, "IT": 0.2, "ES": 0.1, "NL": 0.1, "BE": 0.1},  # 德国、法国、意大利、西班牙、荷兰、比利时
                "+0200": {"FI": 0.2, "GR": 0.2, "RO": 0.2, "BG": 0.1, "IL": 0.1, "ZA": 0.1, "EG": 0.1},  # 芬兰、希腊、罗马尼亚、保加利亚、以色列、南非、埃及
                "+0300": {"RU": 0.5, "TR": 0.3, "SA": 0.2},  # 俄罗斯、土耳其、沙特阿拉伯
                "+0330": {"IR": 0.95},  # 伊朗
                "+0400": {"AE": 0.7, "RU": 0.3},  # 阿联酋、俄罗斯部分
                "+0430": {"AF": 0.95},  # 阿富汗
                "+0545": {"NP": 0.95},  # 尼泊尔
                "+0600": {"BD": 0.7, "RU": 0.3},  # 孟加拉国、俄罗斯部分
                "+0630": {"MM": 0.95},  # 缅甸
                "+0700": {"TH": 0.4, "VN": 0.3, "ID": 0.2, "RU": 0.1},  # 泰国、越南、印度尼西亚、俄罗斯部分
                "+0930": {"AU": 0.95},  # 澳大利亚中部
                "+1000": {"AU": 0.8, "RU": 0.2},  # 澳大利亚东部、俄罗斯部分
                "+1100": {"NC": 0.7, "RU": 0.3},  # 新喀里多尼亚、俄罗斯部分
                "+1200": {"NZ": 0.9, "FJ": 0.1},  # 新西兰、斐济
                "-0300": {"BR": 0.6, "AR": 0.3, "UY": 0.1},  # 巴西、阿根廷、乌拉圭
                "-0200": {"BR": 0.9, "GS": 0.1},  # 巴西部分地区、南乔治亚岛
                "-0100": {"CV": 0.9, "PT": 0.1},  # 佛得角、葡萄牙(亚速尔群岛)
                "-0900": {"US": 0.95},  # 美国阿拉斯加
                "-1000": {"US": 0.95},  # 美国夏威夷
            }
            
            # 检查时区是否在映射中
            if most_common_tz in tz_country_map:
                # 获取该时区对应的国家概率分布
                country_probs = tz_country_map[most_common_tz]
                
                # 选择概率最高的国家
                primary_country = max(country_probs.items(), key=lambda x: x[1])
                country_code = primary_country[0]
                country_prob = primary_country[1]
                
                evidence["timezone"] = country_code
                
                # 根据样本量和时区唯一性调整置信度
                # 样本量越大，置信度越高
                sample_factor = min(0.3, tz_count / 50)
                
                # 时区的唯一性影响置信度
                uniqueness_factor = country_prob * 0.3
                
                confidence_scores["timezone"] = 0.5 + sample_factor + uniqueness_factor
                
                evidence_details["timezone"] = {
                    "source": "提交时区",
                    "raw_value": most_common_tz,
                    "mapped_value": country_code,
                    "probability": country_prob,
                    "count": tz_count,
                    "confidence": confidence_scores["timezone"]
                }
                
                logger.info(f"从时区 {most_common_tz} 推测国家代码: {country_code}, 置信度: {confidence_scores['timezone']:.2f}")
            else:
                logger.info(f"时区 {most_common_tz} 不在已知映射中")
        else:
            logger.info(f"用户 '{username}' 没有足够的提交时区数据")
    except Exception as e:
        logger.warning(f"分析用户 '{username}' 的提交时区时发生错误: {str(e)}")
    
    # 分析活动模式
    try:
        activity_data = analyze_activity_patterns(username)
        if activity_data:
            estimated_tz = activity_data.get("estimated_timezone")
            logger.info(f"用户 '{username}' 的活动模式估计时区: {estimated_tz}")
            
            # 将活动模式估计的时区转换为标准格式
            if estimated_tz and len(estimated_tz) >= 5:
                # 提取小时部分
                hours_part = estimated_tz[0:3]
                
                # 构建查询时区
                query_tz = f"{hours_part}00"
                
                # 使用与提交时区相同的映射
                tz_country_map = {
                    "+0800": {"CN": 0.7, "SG": 0.2, "MY": 0.1},
                    "+0900": {"JP": 0.7, "KR": 0.3},
                    "+0530": {"IN": 0.95},
                    "+0000": {"GB": 0.5, "PT": 0.2, "IS": 0.1, "GH": 0.1, "IE": 0.1},
                    "-0400": {"US": 0.6, "CA": 0.3, "BR": 0.1},
                    "-0500": {"US": 0.8, "CA": 0.2},
                    "-0600": {"US": 0.8, "MX": 0.2},
                    "-0700": {"US": 0.9, "CA": 0.1},
                    "-0800": {"US": 0.95},
                    "+0100": {"DE": 0.3, "FR": 0.2, "IT": 0.2, "ES": 0.1, "NL": 0.1, "BE": 0.1},
                    "+0200": {"FI": 0.2, "GR": 0.2, "RO": 0.2, "BG": 0.1, "IL": 0.1, "ZA": 0.1, "EG": 0.1},
                    "+0300": {"RU": 0.5, "TR": 0.3, "SA": 0.2},
                    "+0330": {"IR": 0.95},
                    "+0400": {"AE": 0.7, "RU": 0.3},
                    "+0430": {"AF": 0.95},
                    "+0545": {"NP": 0.95},
                    "+0600": {"BD": 0.7, "RU": 0.3},
                    "+0630": {"MM": 0.95},
                    "+0700": {"TH": 0.4, "VN": 0.3, "ID": 0.2, "RU": 0.1},
                    "+0930": {"AU": 0.95},
                    "+1000": {"AU": 0.8, "RU": 0.2},
                    "+1100": {"NC": 0.7, "RU": 0.3},
                    "+1200": {"NZ": 0.9, "FJ": 0.1},
                    "-0300": {"BR": 0.6, "AR": 0.3, "UY": 0.1},
                    "-0200": {"BR": 0.9, "GS": 0.1},
                    "-0100": {"CV": 0.9, "PT": 0.1},
                    "-0900": {"US": 0.95},
                    "-1000": {"US": 0.95},
                }
                
                if query_tz in tz_country_map:
                    # 获取该时区对应的国家概率分布
                    country_probs = tz_country_map[query_tz]
                    
                    # 选择概率最高的国家
                    primary_country = max(country_probs.items(), key=lambda x: x[1])
                    country_code = primary_country[0]
                    country_prob = primary_country[1]
                    
                    evidence["activity"] = country_code
                    
                    # 根据活动数据量调整置信度
                    total_events = activity_data.get("total_events", 0)
                    active_dates = activity_data.get("active_dates", 0)
                    
                    # 活动数据越多，置信度越高
                    data_factor = min(0.2, (total_events / 100) + (active_dates / 20))
                    
                    # 周末活动比例影响置信度（如果周末活动比例不符合预期，降低置信度）
                    weekend_ratio = activity_data.get("weekend_ratio", 0)
                    weekend_factor = 0.1 if 0.2 <= weekend_ratio <= 0.4 else 0  # 正常周末活动比例应在20%-40%
                    
                    # 降低活动模式的基础权重，因为它比提交时区更不可靠
                    confidence_scores["activity"] = 0.2 + data_factor + weekend_factor
                    
                    evidence_details["activity"] = {
                        "source": "活动模式",
                        "raw_value": estimated_tz,
                        "mapped_value": country_code,
                        "probability": country_prob,
                        "events": total_events,
                        "active_dates": active_dates,
                        "confidence": confidence_scores["activity"]
                    }
                    
                    logger.info(f"从活动模式推测国家代码: {country_code}, 置信度: {confidence_scores['activity']:.2f}")
    except Exception as e:
        logger.warning(f"分析用户 '{username}' 的活动模式时发生错误: {str(e)}")
    
    # 分析社交网络
    try:
        social_data = analyze_social_network(username)
        if social_data and len(social_data) > 0:
            # 获取前三个最常见位置
            top_locations = social_data[:min(3, len(social_data))]
            logger.info(f"用户 '{username}' 社交网络中最常见的位置: {top_locations}")
            
            # 计算总权重
            total_weight = sum([x[1] for x in social_data])
            
            # 处理每个位置
            for i, (location, weight) in enumerate(top_locations):
                geo_country = geocode_location(location)
                if geo_country:
                    # 为每个位置创建单独的证据
                    evidence_key = f"social_{i+1}"
                    evidence[evidence_key] = geo_country
                    
                    # 计算该位置的权重占比
                    weight_ratio = weight / total_weight if total_weight > 0 else 0
                    
                    # 根据权重比例和排名调整置信度
                    rank_factor = 0.1 if i == 0 else 0.05 if i == 1 else 0.02  # 排名越高权重越大
                    concentration_factor = min(0.2, weight_ratio * 0.5)  # 权重集中度
                    
                    # 降低社交网络的基础权重，因为它比时区和个人资料更不可靠
                    confidence_scores[evidence_key] = 0.2 + rank_factor + concentration_factor
                    
                    # 如果社交网络样本量太小（少于3个关注者），进一步降低置信度
                    if total_weight < 3:
                        confidence_scores[evidence_key] *= 0.8
                        logger.info(f"社交网络样本量较小，降低置信度至: {confidence_scores[evidence_key]:.2f}")
                    
                    evidence_details[evidence_key] = {
                        "source": f"社交网络位置{i+1}",
                        "raw_value": location,
                        "mapped_value": geo_country,
                        "weight": weight,
                        "weight_ratio": weight_ratio,
                        "confidence": confidence_scores[evidence_key]
                    }
                    
                    logger.info(f"从社交网络位置 '{location}' 识别出国家代码: {geo_country}, 置信度: {confidence_scores[evidence_key]:.2f}")
        else:
            logger.info(f"用户 '{username}' 没有足够的社交网络数据")
    except Exception as e:
        logger.warning(f"分析用户 '{username}' 的社交网络时发生错误: {str(e)}")
    
    # 分析语言文化线索
    try:
        language_data = analyze_language_culture_hints(username)
        if language_data:
            # 使用合并后的语言结果
            combined_languages = language_data.get("combined_languages", [])
            if combined_languages and len(combined_languages) > 0:
                # 语言到国家的映射
                lang_country_map = {
                    "Chinese": "CN",
                    "Japanese": "JP",
                    "Korean": "KR",
                    "Russian": "RU",
                    "Arabic": "SA",  # 沙特阿拉伯作为阿拉伯语的代表国家
                    "Hindi": "IN",
                    "Thai": "TH",
                    "Hebrew": "IL",
                    "Spanish": "ES",
                    "French": "FR",
                    "German": "DE",
                    "Portuguese": "BR",  # 巴西作为葡萄牙语使用人数最多的国家
                    "Italian": "IT"
                }
                
                # 处理前两种最常见的语言
                for i, (lang, count) in enumerate(combined_languages[:min(2, len(combined_languages))]):
                    logger.info(f"用户 '{username}' 检测到的语言: {lang}, 权重: {count}")
                    if lang in lang_country_map:
                        evidence_key = f"language_{i+1}"
                        evidence[evidence_key] = lang_country_map[lang]
                        
                        # 根据语言的独特性和计数调整置信度
                        # 某些语言（如中文、日文、韩文）更具地域特征
                        uniqueness_factor = 0.2 if lang in ["Chinese", "Japanese", "Korean", "Russian", "Thai", "Hebrew"] else 0.1
                        count_factor = min(0.2, count / 10)  # 出现次数越多越可信
                        
                        # 降低语言文化线索的基础权重，因为它比其他线索更不可靠
                        confidence_scores[evidence_key] = 0.2 + uniqueness_factor + count_factor
                        
                        evidence_details[evidence_key] = {
                            "source": f"语言文化线索{i+1}",
                            "raw_value": lang,
                            "mapped_value": lang_country_map[lang],
                            "count": count,
                            "confidence": confidence_scores[evidence_key]
                        }
                        
                        logger.info(f"从语言 {lang} 推测国家代码: {lang_country_map[lang]}, 置信度: {confidence_scores[evidence_key]:.2f}")
            else:
                logger.info(f"用户 '{username}' 没有足够的语言文化线索")
        else:
            logger.info(f"用户 '{username}' 没有语言文化数据")
    except Exception as e:
        logger.warning(f"分析用户 '{username}' 的语言文化线索时发生错误: {str(e)}")
    
    # 计算最终预测和置信度
    logger.info(f"用户 '{username}' 的证据收集完成: {evidence}")
    logger.info(f"用户 '{username}' 的各证据置信度: {confidence_scores}")
    
    if not evidence:
        logger.warning(f"用户 '{username}' 没有足够的证据来预测国家")
        return {
            "predicted_country": "Unknown", 
            "confidence": 0, 
            "evidence": {},
            "evidence_details": {}
        }
    
    # 统计每个国家的证据和加权置信度
    country_scores = {}
    for source, country in evidence.items():
        if country not in country_scores:
            country_scores[country] = 0
        country_scores[country] += confidence_scores[source]
    
    logger.info(f"用户 '{username}' 的国家得分统计: {country_scores}")
    
    # 找出得分最高的国家
    if not country_scores:
        logger.warning(f"用户 '{username}' 的国家得分为空")
        return {
            "predicted_country": "Unknown", 
            "confidence": 0, 
            "evidence": {},
            "evidence_details": {}
        }
        
    predicted_country = max(country_scores.items(), key=lambda x: x[1])
    
    # 计算总体置信度（0-1之间）
    # 使用最高分国家的得分除以所有证据的总置信度
    total_confidence = min(1.0, predicted_country[1] / sum(confidence_scores.values())) if confidence_scores else 0
    
    # 改进冲突处理逻辑
    other_countries = [c for c in country_scores.keys() if c != predicted_country[0]]
    if other_countries:
        # 计算证据的一致性
        evidence_count = len(evidence)
        max_country_evidence_count = sum(1 for c in evidence.values() if c == predicted_country[0])
        evidence_consistency = max_country_evidence_count / evidence_count if evidence_count > 0 else 0
        
        # 如果有多个国家的证据，检查冲突程度
        second_best = max([country_scores[c] for c in other_countries]) if other_countries else 0
        conflict_ratio = second_best / predicted_country[1] if predicted_country[1] > 0 else 0
        
        # 根据冲突程度和证据一致性调整置信度
        if conflict_ratio > 0.8:
            # 严重冲突，大幅降低置信度
            confidence_reduction = 0.6
            logger.info(f"检测到严重的证据冲突，降低置信度")
        elif conflict_ratio > 0.5:
            # 中度冲突，适度降低置信度
            confidence_reduction = 0.4
            logger.info(f"检测到中度的证据冲突，降低置信度")
        elif conflict_ratio > 0.3:
            # 轻度冲突，轻微降低置信度
            confidence_reduction = 0.2
            logger.info(f"检测到轻度的证据冲突，降低置信度")
        else:
            # 几乎没有冲突，不降低置信度
            confidence_reduction = 0
        
        # 根据证据一致性调整降低幅度
        if evidence_consistency > 0.7:
            # 证据高度一致，减轻降低幅度
            confidence_reduction *= 0.5
        
        # 应用降低幅度
        total_confidence *= (1 - confidence_reduction)
        logger.info(f"冲突比率: {conflict_ratio:.2f}, 证据一致性: {evidence_consistency:.2f}, 置信度调整为: {total_confidence:.2f}")
    
    logger.info(f"用户 '{username}' 的最终预测国家: {predicted_country[0]}, 置信度: {total_confidence:.2f}")
    
    # 确定置信度级别
    if total_confidence > 0.8:
        confidence_level = "高"
    elif total_confidence > 0.5:
        confidence_level = "中"
    elif total_confidence > 0.3:
        confidence_level = "低"
    else:
        confidence_level = "极低"
    
    return {
        "predicted_country": predicted_country[0],
        "confidence": total_confidence,
        "confidence_level": confidence_level,
        "evidence": evidence,
        "evidence_details": evidence_details,
        "country_scores": country_scores
    }

def predict_developer_country(username):
    """
    综合多种方法推测开发者所在国家，并提供详细分析结果
    """
    logger = logging.getLogger(__name__)
    logger.info(f"开始分析用户 '{username}' 的国家/地区信息")
    
    results = {}
    
    try:
        # 1. 直接信息 - 从个人资料中获取
        try:
            profile = get_user_profile(username)
            results["profile_location"] = profile if profile else {}
            logger.info(f"获取到用户 '{username}' 的基本资料信息")
            # 如果 profile_location 里包含国家信息，则直接返回
            if profile and profile.get("国家") and profile["国家"].strip():
                logger.info(f"用户 '{username}' 的国家信息已在个人资料中找到: {profile['国家']}，无需进一步分析")
                results["prediction"] = {
                    "predicted_country": profile["国家"],
                    "confidence": 1.0,  # 置信度设为 1，表示是明确的信息
                    "confidence_level": "高",
                    "evidence": {"source": "profile_location"},
                    "evidence_details": {"location": profile["国家"]}
                }
                return results
        except Exception as e:
            logger.warning(f"获取用户 '{username}' 的基本资料失败: {str(e)}")
            results["profile_location"] = {}
        
        # 2. 时区分析
        try:
            commit_timezone = analyze_commit_timezone(username)
            logger.info(f"获取到用户 '{username}' 的提交时区信息: {commit_timezone}")
        except Exception as e:
            logger.warning(f"分析用户 '{username}' 的提交时区失败: {str(e)}")
            commit_timezone = None
            
        try:
            activity_patterns = analyze_activity_patterns(username)
            logger.info(f"获取到用户 '{username}' 的活动模式信息")
        except Exception as e:
            logger.warning(f"分析用户 '{username}' 的活动模式失败: {str(e)}")
            activity_patterns = None
        
        results["timezone_analysis"] = {
            "commit_timezone": commit_timezone,
            "activity_patterns": activity_patterns
        }
        
        # 3. 社交网络分析
        try:
            social_network = analyze_social_network(username)
            logger.info(f"获取到用户 '{username}' 的社交网络信息")
        except Exception as e:
            logger.warning(f"分析用户 '{username}' 的社交网络失败: {str(e)}")
            social_network = None
            
        results["social_network"] = social_network
        
        # 4. 语言和文化线索
        try:
            language_culture = analyze_language_culture_hints(username)
            logger.info(f"获取到用户 '{username}' 的语言文化线索")
        except Exception as e:
            logger.warning(f"分析用户 '{username}' 的语言文化线索失败: {str(e)}")
            language_culture = None
            
        results["language_culture"] = language_culture
        
        # 5. 综合预测结果
        try:
            prediction = predict_country_with_confidence(username)
            logger.info(f"完成用户 '{username}' 的国家预测: {prediction.get('predicted_country', 'Unknown')}, 置信度: {prediction.get('confidence', 0)}")
        except Exception as e:
            logger.warning(f"预测用户 '{username}' 的国家失败: {str(e)}")
            prediction = {
                "predicted_country": "Unknown", 
                "confidence": 0, 
                "confidence_level": "低",
                "evidence": {},
                "evidence_details": {}
            }
            
        results["prediction"] = prediction
        
        return results
        
    except Exception as e:
        logger.error(f"分析用户 '{username}' 的国家/地区信息时发生错误: {str(e)}", exc_info=True)
        # 返回部分结果而不是None，确保API不会因此崩溃
        return {
            "profile_location": {},
            "timezone_analysis": {"commit_timezone": None, "activity_patterns": None},
            "social_network": None,
            "language_culture": None,
            "prediction": {
                "predicted_country": "Unknown", 
                "confidence": 0, 
                "confidence_level": "低",
                "evidence": {},
                "evidence_details": {}
            },
            "error": str(e)
        }
