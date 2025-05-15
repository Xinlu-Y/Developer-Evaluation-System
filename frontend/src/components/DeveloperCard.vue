<template>
  <el-card class="developer-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <div class="user-info">
          <el-avatar
            :size="50"
            :src="developer.profile.avatar_url || `https://github.com/${developer.username}.png`"
            class="avatar"
          >
            {{ developer.username ? developer.username.charAt(0).toUpperCase() : '' }}
          </el-avatar>
          <div class="user-details">
            <h3>{{ developer.username }}</h3>
            <p v-if="developer.profile.name">{{ developer.profile.name }}</p>
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

      <template v-if="!hideCountryPrediction">
      <el-divider />
      <div class="info-section">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="国家">
            <el-tag size="small" v-if="developer.profile.国家">
              {{ developer.profile.国家 }}
            </el-tag>
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
                <el-progress :percentage="getPercentage(score)" :color="getColorByScore(score)" :format="(pct) => `${pct}%`"></el-progress>
              </div>
            </div>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </template>


      <!-- 领域分析 -->
      <div v-if="hasDomainData" class="section">
        <div class="section-header">
          <h4>技术领域分析</h4>
          <el-tag type="success">{{ developer.domains.length }}个领域</el-tag>
        </div>
        <!-- <pre style="background:#f6f6f6; padding:1em; font-size:12px;">{{ JSON.stringify(developer.domains, null, 2) }}</pre> -->
        <DomainChart
          v-if="hasDomainData"
          :domains="developer.domains"
          :language-character-stats="developer.language_character_stats"
          no-data-message="未能检测到技术领域"
        />
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
      <template v-if="!hideSkillSummary">
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
              <el-icon><Cpu /></el-icon>
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
      </template>
    </div>
  </el-card>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue'
import DomainChart from './DomainChart.vue'
import axios from 'axios'
import { markdownToHtml } from '../utils/markdown'
import { getDeveloperSkills } from '../api/github'
import { ElMessage } from 'element-plus'
import { Cpu, Document } from '@element-plus/icons-vue'

export default {
  name: 'DeveloperCard',
  components: {
    DomainChart,
    Cpu,
    Document
  },
  props: {
    developer: { type: Object, required: true },
    hideCountryPrediction: { type: Boolean, default: false },
    hideSkillSummary:    { type: Boolean, default: false }
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
      return Array.isArray(this.developer.domains) && this.developer.domains.length > 0;
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
      return confidence ? Math.round(confidence * 100) + '%' : '0%';
    },
    openGithub() {
      const url = this.developer.profile.html_url 
                   || `https://github.com/${this.developer.username}`
      window.open(url, '_blank')
    },
    openRepo(repoName) {
      const username = this.developer.username;
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
      const totalScore = Object.values(this.developer.country_prediction.country_scores).reduce((sum, s) => sum + s, 0);
      return Math.round((score / totalScore) * 100);
    },
    getColorByScore(score) {
      const maxScore = Math.max(...Object.values(this.developer.country_prediction.country_scores));
      const ratio = score / maxScore;
      if (ratio > 0.8) return '#67C23A';
      if (ratio > 0.5) return '#E6A23C';
      return '#909399';
    },
    getCountryName(countryCode) {
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
    async generateSkillSummary() {
      if (!this.developer?.profile?.用户名) {
        ElMessage.error('无法获取开发者信息');
        return;
      }
      
      const username = this.developer.profile.用户名;
      this.loadingSkills = true;
      this.isStreaming = true;
      this.streamingText = '';
      
      try {
        const response = await getDeveloperSkills(username);
        if (response?.data?.skill_summary) {
          this.developer.model = response.data.model || 'AI';
          await this.streamText(response.data.skill_summary);
          this.developer.skill_summary = response.data.skill_summary;
          ElMessage({
            message: '技术能力总结生成成功',
            type: 'success',
            duration: 3000
          });
        } else {
          throw new Error('生成总结数据格式错误');
        }
      } catch (error) {
        console.error('生成技术能力总结失败:', error);
        ElMessage({
          message: error.response?.data?.message || error.message || '生成总结失败，请稍后重试',
          type: 'error',
          duration: 5000
        });
      } finally {
        this.loadingSkills = false;
        this.isStreaming = false;
      }
    },
    
    async streamText(text) {
      return new Promise((resolve) => {
        const words = text.split(' ');
        let currentIndex = 0;
        
        const animate = () => {
          const chunk = 3; // 每次处理3个词
          for (let i = 0; i < chunk && currentIndex < words.length; i++) {
            this.streamingText += words[currentIndex] + ' ';
            currentIndex++;
          }
          
          if (currentIndex < words.length) {
            requestAnimationFrame(animate);
          } else {
            resolve();
          }
        };
        
        requestAnimationFrame(animate);
      });
    }
  },
  
  beforeUnmount() {
    // 清理未完成的异步操作
    this.loadingSkills = false;
    this.isStreaming = false;
  }
}
</script>

<style scoped>
.developer-card {
  border: none;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: rgba(15, 15, 15, 0.05) 0px 0px 0px 1px, rgba(15, 15, 15, 0.1) 0px 3px 6px;
  transition: all 0.3s;
  margin-bottom: 32px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.developer-card:hover {
  box-shadow: rgba(15, 15, 15, 0.1) 0px 0px 0px 1px, rgba(15, 15, 15, 0.2) 0px 3px 6px;
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  border-bottom: 1px solid rgba(55, 53, 47, 0.16);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 24px;
}

.avatar {
  width: 64px !important;
  height: 64px !important;
  border: 1px solid rgba(55, 53, 47, 0.16);
  transition: all 0.3s;
}

.avatar:hover {
  border-color: rgb(55, 53, 47);
}

.user-details h3 {
  color: rgb(55, 53, 47);
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}

.user-details p {
  color: rgba(55, 53, 47, 0.65);
  font-size: 16px;
}

.actions {
  display: flex;
  gap: 12px;
}

.actions .el-button {
  background-color: rgb(55, 53, 47);
  border-color: rgb(55, 53, 47);
  color: #ffffff;
  padding: 8px 16px;
  font-size: 15px;
  border-radius: 8px;
  height: 40px;
}

.actions .el-button:hover {
  background-color: rgba(55, 53, 47, 0.85);
  border-color: rgba(55, 53, 47, 0.85);
}

.card-content {
  padding: 32px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 32px;
}

.stat-item {
  text-align: center;
  padding: 24px;
  background: rgba(55, 53, 47, 0.03);
  border-radius: 12px;
  transition: all 0.3s;
}

.stat-item:hover {
  background: rgba(55, 53, 47, 0.08);
}

.stat-value {
  color: rgb(55, 53, 47);
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 8px;
}

.stat-label {
  color: rgba(55, 53, 47, 0.65);
  font-size: 15px;
}

.info-section {
  margin-top: 32px;
}

.info-section :deep(.el-descriptions) {
  padding: 24px;
  background: rgba(55, 53, 47, 0.03);
  border-radius: 12px;
}

.info-section :deep(.el-descriptions__label) {
  color: rgb(55, 53, 47);
  font-weight: 500;
}

.info-section :deep(.el-descriptions__content) {
  color: rgba(55, 53, 47, 0.65);
}

.section {
  margin-top: 32px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.section-header h4 {
  color: rgb(55, 53, 47);
  font-size: 18px;
  font-weight: 600;
}

.prediction-details {
  margin-top: 16px;
  padding: 20px;
  background: rgba(55, 53, 47, 0.03);
  border-radius: 12px;
}

.evidence-item {
  margin-bottom: 12px;
  padding: 8px;
}

.country-code {
  display: block;
  color: rgb(55, 53, 47);
  font-size: 15px;
  margin-bottom: 8px;
  font-weight: 500;
}

:deep(.el-progress-bar__outer) {
  background-color: rgba(55, 53, 47, 0.1);
  border-radius: 2px;
}

:deep(.el-progress-bar__inner) {
  background-color: rgb(55, 53, 47);
  border-radius: 2px;
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
  background-color: rgba(55, 53, 47, 0.08);
  color: rgb(55, 53, 47);
  border: none;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
}

.generate-btn {
  background-color: rgb(55, 53, 47);
  border-color: rgb(55, 53, 47);
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
}

.generate-btn:hover {
  background-color: rgba(55, 53, 47, 0.85);
  border-color: rgba(55, 53, 47, 0.85);
}

.skill-summary {
  position: relative;
  margin-top: 24px;
  padding: 32px;
  background: rgba(55, 53, 47, 0.03);
  border-radius: 12px;
  border: 1px solid rgba(55, 53, 47, 0.16);
}

.skill-content {
  line-height: 1.8;
  color: rgb(55, 53, 47);
  font-size: 15px;
}

.skill-content :deep(h3) {
  color: rgb(55, 53, 47);
  font-size: 18px;
  font-weight: 600;
  margin: 24px 0 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(55, 53, 47, 0.16);
}

.skill-content :deep(h4) {
  color: rgb(55, 53, 47);
  font-size: 16px;
  font-weight: 500;
  margin: 20px 0 12px;
}

.skill-content :deep(ul) {
  padding-left: 24px;
  margin: 12px 0;
}

.skill-content :deep(li) {
  margin-bottom: 8px;
  color: rgba(55, 53, 47, 0.65);
  line-height: 1.6;
}

.skill-content :deep(p) {
  margin: 12px 0;
  color: rgba(55, 53, 47, 0.65);
  line-height: 1.6;
}

.skill-content :deep(code) {
  background: rgba(55, 53, 47, 0.08);
  color: rgb(55, 53, 47);
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 13px;
}

.streaming-indicator {
  position: absolute;
  bottom: 24px;
  right: 24px;
  display: flex;
  gap: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  background: rgb(55, 53, 47);
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
  padding: 32px;
  background: rgba(55, 53, 47, 0.03);
  border-radius: 12px;
  border: 1px solid rgba(55, 53, 47, 0.16);
}

.skill-summary-empty {
  padding: 48px 32px;
  text-align: center;
  background: rgba(55, 53, 47, 0.03);
  border-radius: 12px;
  border: 1px solid rgba(55, 53, 47, 0.16);
}

.empty-icon {
  font-size: 64px;
  color: rgb(55, 53, 47);
  margin-bottom: 24px;
}

@media (max-width: 768px) {
  .card-header {
    padding: 20px;
  }

  .card-content {
    padding: 20px;
  }

  .stats-row {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .stat-item {
    padding: 16px;
  }

  .skill-summary {
    padding: 20px;
  }

  .skill-summary-empty {
    padding: 32px 20px;
  }

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }
}
</style> 