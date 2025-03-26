<template>
  <el-card class="developer-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <div class="user-info">
          <el-avatar :size="50" :src="`https://github.com/${developer.profile.用户名}.png`" class="avatar">
            {{ developer.profile.用户名.charAt(0).toUpperCase() }}
          </el-avatar>
          <div class="user-details">
            <h3>{{ developer.profile.用户名 }}</h3>
            <p v-if="developer.profile.全名">{{ developer.profile.全名 }}</p>
          </div>
        </div>
        <div class="actions">
          <el-button type="primary" size="small" @click="openGithub">
            <i class="el-icon-link"></i> GitHub主页
          </el-button>
        </div>
      </div>
    </template>

    <div class="card-content">
      <div class="stats-row">
        <div class="stat-item">
          <div class="stat-value">{{ developer.total_stars || 0 }}</div>
          <div class="stat-label">获得的Star</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ developer.profile.关注者数 || 0 }}</div>
          <div class="stat-label">粉丝数</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ formatScore(developer.talent_rank_score) }}</div>
          <div class="stat-label">最终评分</div>
        </div>
      </div>

      <el-divider></el-divider>

      <div class="info-section">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="国家">
            <el-tag size="small" v-if="developer.profile.国家">{{ developer.profile.国家 }}</el-tag>
            <span v-else>当前位置未公开，我们可以预测看看🤔</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 国家预测结果 -->
      <div v-if="!developer.profile.国家 && developer.country_prediction" class="section">
        <div class="section-header">
          <h4>国家预测</h4>
          <el-tag :type="getPredictionTagType(developer.country_prediction.confidence)" size="small">
            {{ getPredictionConfidenceText(developer.country_prediction.confidence_level) }}
          </el-tag>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="预测结果">
            <template v-if="developer.country_prediction.should_display">
              <span>{{ developer.country_prediction.formatted_prediction }}</span>
            </template>
            <template v-else-if="developer.country_prediction.predicted_country && developer.country_prediction.predicted_country !== 'Unknown'">
              <span>{{ getCountryName(developer.country_prediction.predicted_country) }} (置信度: {{ formatConfidence(developer.country_prediction.confidence) }})</span>
            </template>
            <template v-else>
              <span>未知</span>
            </template>
          </el-descriptions-item>
          <el-descriptions-item v-if="showPredictionDetails" label="预测依据">
            <el-button type="text" @click="togglePredictionDetails">
              {{ showDetails ? '隐藏详情' : '查看详情' }}
            </el-button>
            <div v-if="showDetails" class="prediction-details">
              <div v-for="(score, country) in developer.country_prediction.country_scores" :key="country" class="evidence-item">
                <span class="country-code">{{ getCountryName(country) }}:</span>
                <el-progress :percentage="getPercentage(score)" :color="getColorByScore(score)"></el-progress>
              </div>
            </div>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 领域分析 -->
      <div v-if="hasDomainData" class="section">
        <div class="section-header">
          <h4>技术领域分析</h4>
          <el-tag type="success">{{ Object.keys(developer.domains).length }}个领域</el-tag>
        </div>
        <domain-chart :domains="developer.domains" :no-data-message="'未能检测到技术领域'"></domain-chart>
      </div>

      <!-- 个人项目 -->
      <div v-if="developer.repositories?.length" class="section">
        <div class="section-header">
          <h4>个人项目</h4>
          <el-tag type="success">{{ developer.repositories.length }}个项目</el-tag>
        </div>
        <el-table :data="developer.repositories" stripe style="width: 100%" :max-height="300">
          <el-table-column prop="repo_name" label="项目名称" min-width="120">
            <template #default="scope">
              <el-tooltip :content="scope.row.repo_description" placement="top" :disabled="!scope.row.repo_description">
                <el-link type="primary" @click="openRepo(scope.row.repo_name)">{{ scope.row.repo_name }}</el-link>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="repo_description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column prop="Star" label="Star数" width="100">
            <template #default="scope">
              <span class="star-count">⭐ {{ scope.row.Star }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="Fork" label="Fork数" width="100">
            <template #default="scope">
              <span class="fork-count">🍴 {{ scope.row.Fork }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 贡献项目 -->
      <div v-if="developer.contributions?.length" class="section">
        <div class="section-header">
          <h4>参与的项目</h4>
          <el-tag type="warning">{{ developer.contributions.length }}个项目</el-tag>
        </div>
        <el-table :data="developer.contributions" stripe style="width: 100%" :max-height="300">
          <el-table-column prop="repo_name" label="项目名称" min-width="150" />
          <el-table-column prop="repo_star" label="Star数" width="100">
            <template #default="scope">
              <span class="star-count">⭐ {{ scope.row.Star }}</span>
            </template>
          </el-table-column>
          <el-table-column label="项目地址" min-width="200">
            <template #default="scope">
              <el-link type="primary" :href="scope.row.html_url" target="_blank" :underline="false">
                查看项目
              </el-link>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 技术能力总结 -->
      <div class="section">
        <div class="section-header">
          <h4>技术能力总结</h4>
          <div class="section-actions">
            <el-tag type="primary" v-if="developer.skill_summary" class="model-tag">
              {{ developer.model || 'AI' }}生成
            </el-tag>
            <el-button 
              v-else 
              type="primary" 
              size="small" 
              @click="generateSkillSummary" 
              :loading="loadingSkills"
              class="generate-btn"
            >
              <el-icon><Magic /></el-icon>
              生成总结
            </el-button>
          </div>
        </div>
        
        <div v-if="developer.skill_summary" class="skill-summary">
          <div class="skill-content" v-html="formattedSkillSummary"></div>
          <div v-if="isStreaming" class="streaming-indicator">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
        
        <div v-else-if="loadingSkills" class="skill-summary-loading">
          <el-skeleton :rows="6" animated />
        </div>
        
        <div v-else class="skill-summary-empty">
          <el-empty 
            description="点击上方按钮生成开发者技术能力总结" 
            :image-size="100"
          >
            <template #image>
              <el-icon class="empty-icon"><Document /></el-icon>
            </template>
          </el-empty>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script>
import DomainChart from './DomainChart.vue'
import axios from 'axios'
import { markdownToHtml } from '../utils/markdown'
import { getDeveloperSkills } from '../api/github'
import { ElMessage } from 'element-plus'
import { Magic, Document } from '@element-plus/icons-vue'

export default {
  name: 'DeveloperCard',
  components: {
    DomainChart,
    Magic,
    Document
  },
  props: {
    developer: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      showDetails: false,
      loadingSkills: false,
      isStreaming: false,
      streamingText: '',
      currentIndex: 0
    }
  },
  computed: {
    showPredictionDetails() {
      return this.developer.country_prediction && 
             this.developer.country_prediction.country_scores && 
             Object.keys(this.developer.country_prediction.country_scores).length > 0;
    },
    hasDomainData() {
      return this.developer.domains && Object.keys(this.developer.domains).length > 0;
    },
    formattedSkillSummary() {
      if (!this.developer.skill_summary) return '';
      // 将简单的Markdown格式转换为HTML
      return markdownToHtml(this.developer.skill_summary);
    }
  },
  methods: {
    formatScore(score) {
      return score ? parseFloat(score).toFixed(2) : '0.00';
    },
    formatConfidence(confidence) {
      return confidence ? (confidence * 100).toFixed(1) + '%' : '0%';
    },
    openGithub() {
      window.open(this.developer.profile['GitHub 个人主页'], '_blank');
    },
    openRepo(repoName) {
      const username = this.developer.profile.用户名;
      window.open(`https://github.com/${username}/${repoName}`, '_blank');
    },
    togglePredictionDetails() {
      this.showDetails = !this.showDetails;
    },
    getPredictionTagType(confidence) {
      if (!confidence) return 'info';
      if (confidence > 0.8) return 'success';
      if (confidence > 0.5) return 'warning';
      return 'info';
    },
    getPredictionConfidenceText(level) {
      if (!level) return '未知';
      const levelMap = {
        '高': '高置信度',
        '中': '中等置信度',
        '低': '低置信度',
        '极低': '极低置信度'
      };
      return levelMap[level] || level;
    },
    getPercentage(score) {
      // 将分数转换为百分比，最高分为100%
      const maxScore = Math.max(...Object.values(this.developer.country_prediction.country_scores));
      return (score / maxScore) * 100;
    },
    getColorByScore(score) {
      // 根据分数返回不同的颜色
      const maxScore = Math.max(...Object.values(this.developer.country_prediction.country_scores));
      const ratio = score / maxScore;
      if (ratio > 0.8) return '#67C23A';
      if (ratio > 0.5) return '#E6A23C';
      return '#909399';
    },
    getCountryName(countryCode) {
      // 国家代码到国家名称的映射
      const countryMap = {
        'CN': '中国',
        'US': '美国',
        'JP': '日本',
        'KR': '韩国',
        'IN': '印度',
        'GB': '英国',
        'CA': '加拿大',
        'AU': '澳大利亚',
        'DE': '德国',
        'FR': '法国',
        'RU': '俄罗斯',
        'BR': '巴西',
        'SG': '新加坡',
        'NL': '荷兰',
        'SE': '瑞典',
        'CH': '瑞士',
        'ES': '西班牙',
        'IT': '意大利',
        'IL': '以色列',
        'FI': '芬兰',
        'PT': '葡萄牙',
        'IS': '冰岛',
        'Unknown': '未知'
      };
      return countryMap[countryCode] || `未知(${countryCode})`;
    },
    // 生成技术能力总结
    async generateSkillSummary() {
      if (!this.developer || !this.developer.profile || !this.developer.profile.用户名) {
        ElMessage.error('无法获取开发者信息');
        return;
      }
      
      const username = this.developer.profile.用户名;
      this.loadingSkills = true;
      this.isStreaming = true;
      this.streamingText = '';
      this.currentIndex = 0;
      
      try {
        const response = await getDeveloperSkills(username);
        if (response.data && response.data.skill_summary) {
          this.developer.model = response.data.model || 'AI';
          await this.streamText(response.data.skill_summary);
          this.developer.skill_summary = response.data.skill_summary;
          ElMessage.success('技术能力总结生成成功');
        } else {
          ElMessage.warning('生成总结时出现问题，请稍后再试');
        }
      } catch (error) {
        console.error('生成技术能力总结失败:', error);
        ElMessage.error('生成总结失败: ' + (error.response?.data?.message || error.message));
      } finally {
        this.loadingSkills = false;
        this.isStreaming = false;
      }
    },
    
    async streamText(text) {
      const words = text.split(' ');
      for (let i = 0; i < words.length; i++) {
        this.streamingText += words[i] + ' ';
        await new Promise(resolve => setTimeout(resolve, 50)); // 控制打字速度
      }
    }
  }
}
</script>

<style scoped>
.developer-card {
  border: none;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
}

.developer-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e5e5e5;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar {
  border: 2px solid #e5e5e5;
  transition: all 0.2s;
}

.avatar:hover {
  border-color: #2eaadc;
}

.user-details h3 {
  color: #37352f;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.user-details p {
  color: #787774;
  font-size: 14px;
}

.actions {
  display: flex;
  gap: 8px;
}

.actions .el-button {
  padding: 6px 12px;
  font-size: 13px;
  border-radius: 4px;
}

.card-content {
  padding: 16px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 6px;
  transition: all 0.2s;
}

.stat-item:hover {
  background: #e8f6fa;
}

.stat-value {
  color: #2eaadc;
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.stat-label {
  color: #787774;
  font-size: 13px;
}

.info-section {
  margin-top: 16px;
}

.info-section :deep(.el-descriptions) {
  padding: 16px;
  background: #f5f5f5;
  border-radius: 6px;
}

.info-section :deep(.el-descriptions__label) {
  color: #37352f;
  font-weight: 500;
}

.info-section :deep(.el-descriptions__content) {
  color: #787774;
}

.section {
  margin-top: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.section-header h4 {
  color: #37352f;
  font-size: 16px;
  font-weight: 600;
}

.prediction-details {
  margin-top: 12px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 6px;
}

.evidence-item {
  margin-bottom: 8px;
}

.evidence-item:last-child {
  margin-bottom: 0;
}

.country-code {
  display: block;
  color: #37352f;
  font-size: 13px;
  margin-bottom: 4px;
}

:deep(.el-progress-bar__outer) {
  background-color: #e5e5e5;
  border-radius: 2px;
}

:deep(.el-progress-bar__inner) {
  background-color: #2eaadc;
  border-radius: 2px;
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .actions {
    width: 100%;
    justify-content: flex-end;
  }
}

.star-count, .fork-count {
  display: flex;
  align-items: center;
  justify-content: center;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
}

.generate-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
}

.skill-summary {
  position: relative;
  margin-top: 16px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e5e5e5;
}

.skill-content {
  line-height: 1.8;
  color: #37352f;
}

.skill-content :deep(h3) {
  color: #2eaadc;
  font-size: 16px;
  font-weight: 600;
  margin: 20px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e5e5;
}

.skill-content :deep(h4) {
  color: #37352f;
  font-size: 14px;
  font-weight: 500;
  margin: 16px 0 8px;
}

.skill-content :deep(ul) {
  padding-left: 20px;
  margin: 8px 0;
}

.skill-content :deep(li) {
  margin-bottom: 6px;
  color: #787774;
}

.skill-content :deep(p) {
  margin: 8px 0;
  color: #787774;
}

.skill-content :deep(code) {
  background: #e8f6fa;
  color: #2eaadc;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 13px;
}

.streaming-indicator {
  position: absolute;
  bottom: 20px;
  right: 20px;
  display: flex;
  gap: 4px;
}

.dot {
  width: 6px;
  height: 6px;
  background: #2eaadc;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.skill-summary-loading {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e5e5e5;
}

.skill-summary-empty {
  padding: 40px 20px;
  text-align: center;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e5e5e5;
}

.empty-icon {
  font-size: 48px;
  color: #2eaadc;
  margin-bottom: 16px;
}

@media (max-width: 768px) {
  .skill-summary {
    padding: 16px;
  }
  
  .streaming-indicator {
    bottom: 16px;
    right: 16px;
  }
}
</style> 