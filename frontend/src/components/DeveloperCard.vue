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
          <div class="stat-label">TalentRank评分</div>
        </div>
      </div>

      <el-divider></el-divider>

      <div class="info-section">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="国家" :span="developer.profile.国家 ? 1 : 2">
            <el-tag size="small" v-if="developer.profile.国家">{{ developer.profile.国家 }}</el-tag>
            <span v-else>未知</span>
          </el-descriptions-item>
          <el-descriptions-item label="邮箱" :span="developer.profile.邮箱 ? 1 : 0">
            <el-link v-if="developer.profile.邮箱" type="primary" :href="`mailto:${developer.profile.邮箱}`">
              {{ developer.profile.邮箱 }}
            </el-link>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 国家预测结果 -->
      <div v-if="developer.country_prediction" class="section">
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
          <el-tag type="warning">{{ developer.contributions.length }}个贡献</el-tag>
        </div>
        <el-table :data="developer.contributions" stripe style="width: 100%" :max-height="300">
          <el-table-column prop="repo_name" label="项目名称" min-width="150" />
          <el-table-column prop="repo_star" label="Star数" width="100">
            <template #default="scope">
              <span class="star-count">⭐ {{ scope.row.repo_star }}</span>
            </template>
          </el-table-column>
          <el-table-column label="项目地址" min-width="200">
            <template #default="scope">
              <el-link type="primary" :href="scope.row.repo_url" target="_blank" :underline="false">
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
          <el-tag type="primary" v-if="developer.skill_summary">{{ developer.model || 'AI' }}生成</el-tag>
          <el-button v-else type="link" size="small" @click="generateSkillSummary" :loading="loadingSkills">
            生成总结
          </el-button>
        </div>
        <div v-if="developer.skill_summary" class="skill-summary">
          <div v-html="formattedSkillSummary"></div>
        </div>
        <div v-else-if="loadingSkills" class="skill-summary-loading">
          <el-skeleton :rows="6" animated />
        </div>
        <div v-else class="skill-summary-empty">
          <el-empty description="点击上方按钮生成开发者技术能力总结" :image-size="100"></el-empty>
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

export default {
  name: 'DeveloperCard',
  components: {
    DomainChart
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
      loadingSkills: false
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
      
      try {
        const response = await getDeveloperSkills(username);
        if (response.data && response.data.skill_summary) {
          // 更新开发者对象的技术能力总结和模型名称
          this.developer.skill_summary = response.data.skill_summary;
          this.developer.model = response.data.model || 'AI';
          ElMessage.success('技术能力总结生成成功');
        } else {
          ElMessage.warning('生成总结时出现问题，请稍后再试');
        }
      } catch (error) {
        console.error('生成技术能力总结失败:', error);
        ElMessage.error('生成总结失败: ' + (error.response?.data?.message || error.message));
      } finally {
        this.loadingSkills = false;
      }
    }
  }
}
</script>

<style scoped>
.developer-card {
  margin-bottom: 20px;
  transition: all 0.3s ease;
  border-radius: 8px;
  overflow: hidden;
}

.developer-card:hover {
  transform: translateY(-5px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.user-info {
  display: flex;
  align-items: center;
}

.avatar {
  margin-right: 15px;
  border: 2px solid #409EFF;
}

.user-details h3 {
  margin: 0 0 5px 0;
  font-size: 18px;
  color: #303133;
}

.user-details p {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.card-content {
  padding: 10px 0;
}

.stats-row {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 0 15px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  margin-top: 5px;
}

.section {
  margin-top: 25px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-header h4 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.star-count, .fork-count {
  display: flex;
  align-items: center;
  justify-content: center;
}

.info-section {
  margin: 20px 0;
}

:deep(.el-descriptions__label) {
  width: 80px;
}

.prediction-details {
  margin-top: 10px;
}

.evidence-item {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.country-code {
  width: 80px;
  font-weight: bold;
  margin-right: 10px;
}

:deep(.el-progress) {
  flex: 1;
}

.skill-summary {
  margin-top: 15px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
  line-height: 1.6;
}

.skill-summary h3 {
  font-size: 16px;
  color: #409EFF;
  margin-top: 15px;
  margin-bottom: 8px;
}

.skill-summary h4 {
  font-size: 14px;
  color: #303133;
  margin-top: 12px;
  margin-bottom: 6px;
}

.skill-summary ul {
  padding-left: 20px;
  margin: 10px 0;
}

.skill-summary li {
  margin-bottom: 5px;
}

.skill-summary p {
  margin: 10px 0;
}

.skill-summary-empty {
  padding: 30px 0;
  text-align: center;
}

.skill-summary-loading {
  padding: 15px;
}

.dev-skill-summary {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.skill-section {
  margin-bottom: 20px;
  padding: 10px 15px;
  border-left: 3px solid #409EFF;
  background-color: rgba(64, 158, 255, 0.05);
  border-radius: 0 4px 4px 0;
}

.skill-section h3 {
  color: #409EFF;
  font-size: 16px;
  margin-top: 0;
  margin-bottom: 12px;
}

.tech-stack {
  border-left-color: #409EFF;
}

.domains {
  border-left-color: #67C23A;
}

.projects {
  border-left-color: #E6A23C;
}

.growth {
  border-left-color: #F56C6C;
}

.collaboration {
  border-left-color: #909399;
}

.tech-highlight {
  background-color: rgba(64, 158, 255, 0.15);
  color: #409EFF;
  padding: 2px 4px;
  border-radius: 3px;
  font-weight: 500;
}

.skill-rating {
  display: flex;
  align-items: center;
  margin: 5px 0;
}

.rating-label {
  min-width: 70px;
  font-weight: 500;
  margin-right: 8px;
}

.rating-stars {
  color: #F56C6C;
  letter-spacing: 2px;
}

code {
  background-color: #f4f4f4;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9em;
}
</style> 