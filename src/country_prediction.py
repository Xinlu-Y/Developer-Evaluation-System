import logging

from geo_utils import geocode_location
from language_culture import analyze_language_culture_hints
from social_network import analyze_social_network
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
                confidence_scores["profile"] = 0.9
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
    
    # 分析社交网络
    try:
        logger.info(f"开始分析用户 '{username}' 的社交网络位置信息...")
        social_data = analyze_social_network(username, depth=3)
        if social_data and len(social_data) > 0:
            # 获取前三个最常见位置
            top_locations = social_data[:min(3, len(social_data))]
            logger.info(f"用户 '{username}' 社交网络中最常见的位置: {top_locations}")
            logger.info(f"社交网络分析共找到 {len(social_data)} 个位置，取前 {len(top_locations)} 个进行分析")
            
            # 计算总权重
            total_weight = sum([x[1] for x in social_data])
            logger.info(f"社交网络位置总权重: {total_weight}")
            
            # 详细记录所有社交网络位置数据
            for idx, (loc, w) in enumerate(social_data):
                logger.info(f"社交网络位置 #{idx+1}: {loc}, 权重: {w}, 占比: {w/total_weight:.4f}")
            
            # 处理每个位置
            for i, (location, weight) in enumerate(top_locations):
                logger.info(f"开始处理社交网络位置 #{i+1}: {location}, 权重: {weight}")
                geo_country = geocode_location(location)
                logger.info(f"位置 '{location}' 地理编码结果: {geo_country}")
                
                if geo_country:
                    # 为每个位置创建单独的证据
                    evidence_key = f"social_{i+1}"
                    evidence[evidence_key] = geo_country
                    
                    # 计算该位置的权重占比
                    weight_ratio = weight / total_weight if total_weight > 0 else 0
                    logger.info(f"位置 '{location}' 权重占比: {weight_ratio:.4f}")
                    
                    # 根据权重比例和排名调整置信度
                    rank_factor = 0.1 if i == 0 else 0.05 if i == 1 else 0.02  # 排名越高权重越大
                    logger.info(f"位置 '{location}' 排名因子: {rank_factor}")
                    
                    concentration_factor = min(0.2, weight_ratio * 0.5)  # 权重集中度
                    logger.info(f"位置 '{location}' 权重集中度因子: {concentration_factor:.4f}")
                    
                    # 由于社交网络深度分析增强，略微提高基础置信度
                    base_confidence = 0.25
                    logger.info(f"位置 '{location}' 基础置信度: {base_confidence}")
                    
                    confidence_scores[evidence_key] = base_confidence + rank_factor + concentration_factor
                    logger.info(f"位置 '{location}' 初始置信度计算: {base_confidence} + {rank_factor} + {concentration_factor:.4f} = {confidence_scores[evidence_key]:.4f}")
                    
                    # 如果社交网络样本量太小（少于3个关注者），进一步降低置信度
                    if total_weight < 3:
                        original_confidence = confidence_scores[evidence_key]
                        confidence_scores[evidence_key] *= 0.8
                        logger.info(f"社交网络样本量较小(总权重={total_weight})，降低置信度: {original_confidence:.4f} * 0.8 = {confidence_scores[evidence_key]:.4f}")
                    
                    evidence_details[evidence_key] = {
                        "source": f"社交网络位置{i+1}",
                        "raw_value": location,
                        "mapped_value": geo_country,
                        "weight": weight,
                        "weight_ratio": weight_ratio,
                        "confidence": confidence_scores[evidence_key]
                    }
                    
                    logger.info(f"从社交网络位置 '{location}' 识别出国家代码: {geo_country}, 最终置信度: {confidence_scores[evidence_key]:.4f}")
                else:
                    logger.info(f"社交网络位置 '{location}' 无法映射到国家代码，忽略此位置")
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
    logger.info(f"开始计算每个国家的总分...")
    for source, country in evidence.items():
        if country not in country_scores:
            country_scores[country] = 0
            logger.info(f"发现新国家: {country}")
        
        original_score = country_scores[country]
        country_scores[country] += confidence_scores[source]
        logger.info(f"国家 {country} 从证据 '{source}' 获得 {confidence_scores[source]:.4f} 分，总分从 {original_score:.4f} 增加到 {country_scores[country]:.4f}")
    
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
    logger.info(f"得分最高的国家是: {predicted_country[0]}，得分: {predicted_country[1]:.4f}")
    
    # 计算总体置信度（0-1之间）
    # 使用最高分国家的得分除以所有证据的总置信度
    total_confidence_score = sum(confidence_scores.values())
    logger.info(f"所有证据的总置信度: {total_confidence_score:.4f}")
    
    total_confidence = min(1.0, predicted_country[1] / total_confidence_score) if confidence_scores else 0
    logger.info(f"初始总体置信度计算: min(1.0, {predicted_country[1]:.4f} / {total_confidence_score:.4f}) = {total_confidence:.4f}")
    
    # 改进冲突处理逻辑
    other_countries = [c for c in country_scores.keys() if c != predicted_country[0]]
    if other_countries:
        logger.info(f"存在其他候选国家: {other_countries}")
        
        # 计算证据的一致性
        evidence_count = len(evidence)
        max_country_evidence_count = sum(1 for c in evidence.values() if c == predicted_country[0])
        evidence_consistency = max_country_evidence_count / evidence_count if evidence_count > 0 else 0
        logger.info(f"证据一致性计算: {max_country_evidence_count} / {evidence_count} = {evidence_consistency:.4f}")
        
        # 如果有多个国家的证据，检查冲突程度
        second_best = max([country_scores[c] for c in other_countries]) if other_countries else 0
        second_best_country = [c for c in other_countries if country_scores[c] == second_best][0] if second_best > 0 else "None"
        logger.info(f"第二高分国家是: {second_best_country}，得分: {second_best:.4f}")
        
        conflict_ratio = second_best / predicted_country[1] if predicted_country[1] > 0 else 0
        logger.info(f"冲突比率计算: {second_best:.4f} / {predicted_country[1]:.4f} = {conflict_ratio:.4f}")
        
        # 根据冲突程度和证据一致性调整置信度
        if conflict_ratio > 0.8:
            # 严重冲突，大幅降低置信度
            confidence_reduction = 0.6
            logger.info(f"检测到严重的证据冲突(冲突比率={conflict_ratio:.4f} > 0.8)，置信度降低因子: {confidence_reduction}")
        elif conflict_ratio > 0.5:
            # 中度冲突，适度降低置信度
            confidence_reduction = 0.4
            logger.info(f"检测到中度的证据冲突(冲突比率={conflict_ratio:.4f} > 0.5)，置信度降低因子: {confidence_reduction}")
        elif conflict_ratio > 0.3:
            # 轻度冲突，轻微降低置信度
            confidence_reduction = 0.2
            logger.info(f"检测到轻度的证据冲突(冲突比率={conflict_ratio:.4f} > 0.3)，置信度降低因子: {confidence_reduction}")
        else:
            # 几乎没有冲突，不降低置信度
            confidence_reduction = 0
            logger.info(f"几乎没有证据冲突(冲突比率={conflict_ratio:.4f} <= 0.3)，不降低置信度")
        
        # 根据证据一致性调整降低幅度
        original_reduction = confidence_reduction
        if evidence_consistency > 0.7:
            # 证据高度一致，减轻降低幅度
            confidence_reduction *= 0.5
            logger.info(f"证据高度一致(一致性={evidence_consistency:.4f} > 0.7)，降低幅度从 {original_reduction} 减轻到 {confidence_reduction}")
        
        # 应用降低幅度
        original_confidence = total_confidence
        total_confidence *= (1 - confidence_reduction)
        logger.info(f"应用置信度调整: {original_confidence:.4f} * (1 - {confidence_reduction}) = {total_confidence:.4f}")
    else:
        logger.info(f"没有其他候选国家，无需处理证据冲突")
    
    logger.info(f"用户 '{username}' 的最终预测国家: {predicted_country[0]}, 置信度: {total_confidence:.4f}")
    
    # 确定置信度级别
    if total_confidence > 0.8:
        confidence_level = "高"
        logger.info(f"置信度 {total_confidence:.4f} > 0.8，判定为高置信度")
    elif total_confidence > 0.5:
        confidence_level = "中"
        logger.info(f"置信度 {total_confidence:.4f} > 0.5，判定为中置信度")
    elif total_confidence > 0.3:
        confidence_level = "低"
        logger.info(f"置信度 {total_confidence:.4f} > 0.3，判定为低置信度")
    else:
        confidence_level = "极低"
        logger.info(f"置信度 {total_confidence:.4f} <= 0.3，判定为极低置信度")
    
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
            
        # 2. 社交网络分析
        try:
            logger.info(f"开始执行用户 '{username}' 的社交网络分析，深度为3...")
            social_network = analyze_social_network(username, depth=3)
            logger.info(f"获取到用户 '{username}' 的社交网络信息: {len(social_network) if social_network else 0} 条位置数据")
        except Exception as e:
            logger.warning(f"分析用户 '{username}' 的社交网络失败: {str(e)}")
            social_network = None
            
        results["social_network"] = social_network
        
        # 3. 语言和文化线索
        try:
            language_culture = analyze_language_culture_hints(username)
            logger.info(f"获取到用户 '{username}' 的语言文化线索")
        except Exception as e:
            logger.warning(f"分析用户 '{username}' 的语言文化线索失败: {str(e)}")
            language_culture = None
            
        results["language_culture"] = language_culture
        
        # 4. 综合预测结果
        try:
            logger.info(f"开始进行用户 '{username}' 的国家综合预测...")
            prediction = predict_country_with_confidence(username)
            logger.info(f"完成用户 '{username}' 的国家预测: {prediction.get('predicted_country', 'Unknown')}, 置信度: {prediction.get('confidence', 0):.4f}, 级别: {prediction.get('confidence_level', '未知')}")
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
