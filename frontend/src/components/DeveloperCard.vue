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
    </div>
  </el-card>
</template>

<script>
export default {
  name: 'DeveloperCard',
  props: {
    developer: {
      type: Object,
      required: true
    }
  },
  methods: {
    formatScore(score) {
      return score ? parseFloat(score).toFixed(2) : '0.00';
    },
    openGithub() {
      window.open(this.developer.profile['GitHub 个人主页'], '_blank');
    },
    openRepo(repoName) {
      const username = this.developer.profile.用户名;
      window.open(`https://github.com/${username}/${repoName}`, '_blank');
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
</style> 