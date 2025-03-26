<template>
  <div class="developer-search">
    <div class="header">
      <h1>GitHub开发者能力评估</h1>
      <p>发现优秀的开发者和他们的项目</p>
    </div>
    
    <el-card class="search-card">
      <el-tabs v-model="activeTab" class="custom-tabs">
        <!-- 用户名搜索 -->
        <el-tab-pane label="基于用户名搜索" name="username">
          <div class="search-container">
            <el-input
              v-model="username"
              placeholder="输入开发者用户名"
              class="search-input"
              prefix-icon="el-icon-search"
            />
            <el-button type="primary" @click="searchByUsername" :loading="loading">搜索</el-button>
          </div>
          
          <!-- 开发者信息卡片 -->
          <transition name="fade">
            <developer-card
              v-if="developer"
              :developer="developer"
            />
          </transition>
        </el-tab-pane>

        <!-- 领域搜索 -->
        <el-tab-pane label="基于领域搜索" name="domain">
          <el-form inline class="domain-form">
            <el-form-item label="编程语言">
              <el-input v-model="domainSearch.language" placeholder="如: python, javascript" />
            </el-form-item>
            <el-form-item label="主题">
              <el-input v-model="domainSearch.topic" placeholder="如: machine-learning, web" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="searchByDomain" :loading="loading">搜索</el-button>
            </el-form-item>
          </el-form>

          <!-- 高级选项 -->
          <div class="advanced-options">
            <el-checkbox v-model="domainSearch.includeSkills" label="包含技术能力总结" border />
            <el-tooltip content="启用此选项将尝试为每个开发者生成技术能力总结，可能会增加搜索时间" placement="top">
              <el-icon class="info-icon"><InfoFilled /></el-icon>
            </el-tooltip>
          </div>

          <!-- 添加加载状态显示 -->
          <div v-if="loading" class="loading-state">
            <el-card class="loading-card">
              <template #header>
                <div class="loading-header">
                  <el-icon class="loading-icon"><Loading /></el-icon>
                  <span>正在搜索中...</span>
                </div>
              </template>
              <p>正在查询符合以下条件的开发者：</p>
              <ul>
                <li>编程语言：{{ domainSearch.language }}</li>
                <li>主题：{{ domainSearch.topic }}</li>
              </ul>
              <p class="loading-tip">这可能需要一些时间，请耐心等待</p>
            </el-card>
          </div>

          <!-- 搜索结果统计 -->
          <div v-if="!loading && searchTime" class="search-stats">
            <el-alert
              :title="`搜索完成！用时 ${searchTime} 秒，共找到 ${total} 个开发者`"
              type="success"
              :closable="false"
              show-icon
            />
          </div>

          <!-- 开发者列表 -->
          <transition-group name="list" tag="div" class="developer-list">
            <developer-card
              v-for="dev in developers"
              :key="dev.profile.用户名"
              :developer="dev"
            />
          </transition-group>

          <!-- 分页 -->
          <el-pagination
            v-if="total > 0"
            :current-page="currentPage"
            :page-size="pageSize"
            :total="total"
            @current-change="handlePageChange"
            layout="prev, pager, next, jumper"
            class="pagination"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { getDeveloperInfo, searchByDomain as searchByDomainAPI } from '../api/github'
import DeveloperCard from '../components/DeveloperCard.vue'
import { ElMessage } from 'element-plus'
import { Loading, InfoFilled } from '@element-plus/icons-vue'

export default {
  name: 'DeveloperSearch',
  components: {
    DeveloperCard,
    Loading,
    InfoFilled
  },
  setup() {
    const activeTab = ref('username')
    const username = ref('')
    const developer = ref(null)
    const developers = ref([])
    const total = ref(0)
    const currentPage = ref(1)
    const pageSize = ref(5)
    const loading = ref(false)
    const searchTime = ref('')
    
    const domainSearch = reactive({
      language: '',
      topic: '',
      includeSkills: false
    })

    const searchByUsername = async () => {
      if (!username.value) {
        ElMessage.warning('请输入用户名')
        return
      }
      
      loading.value = true
      try {
        const loadingMessage = ElMessage({
          message: '正在获取开发者信息，请稍候...',
          type: 'info',
          duration: 0
        })
        
        const { data } = await getDeveloperInfo(username.value)
        developer.value = data
        loadingMessage.close()
        
        // 检查是否成功获取领域数据
        if (data.domains && Object.keys(data.domains).length === 0) {
          ElMessage({
            message: '获取开发者领域信息失败，可能需要刷新重试',
            type: 'warning',
            duration: 5000
          })
        }
      } catch (error) {
        console.error('搜索错误:', error)
        ElMessage.closeAll()
        
        if (error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK' || error.code === 'ECONNRESET') {
          ElMessage({
            message: '连接服务器失败，请确保后端服务正在运行并刷新页面重试',
            type: 'error',
            duration: 5000
          })
        } else {
          ElMessage.error(error.response?.data?.error || '搜索失败，请稍后重试')
        }
      } finally {
        loading.value = false
      }
    }

    const performDomainSearch = async () => {
      if (!domainSearch.language || !domainSearch.topic) {
        ElMessage.warning('请输入语言和主题')
        return
      }
      
      loading.value = true
      developers.value = []
      total.value = 0
      searchTime.value = ''
      
      try {
        const loadingMessage = ElMessage({
          message: '正在搜索开发者，这可能需要一些时间（最长10分钟）...',
          type: 'info',
          duration: 0
        })
        
        const response = await searchByDomainAPI({
          language: domainSearch.language,
          topic: domainSearch.topic,
          offset: (currentPage.value - 1) * pageSize.value,
          limit: pageSize.value,
          include_skills: domainSearch.includeSkills
        })
        
        if (response && response.data) {
          developers.value = response.data.developers || []
          total.value = response.data.total || 0
          searchTime.value = response.data.search_time || ''
          
          loadingMessage.close()
          
          if (response.data.developers.length === 0) {
            ElMessage({
              message: '未找到符合条件的开发者',
              type: 'info',
              duration: 3000
            })
          }
        } else {
          throw new Error('搜索结果格式错误')
        }
      } catch (error) {
        console.error('搜索错误:', error)
        ElMessage.closeAll()
        
        if (error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK' || error.code === 'ECONNRESET') {
          ElMessage({
            message: '连接服务器失败，请确保后端服务正在运行并刷新页面重试',
            type: 'error',
            duration: 5000
          })
        } else {
          ElMessage.error(error.response?.data?.error || '搜索失败，请稍后重试')
        }
        
        // 在错误发生时重置状态
        developers.value = []
        total.value = 0
        searchTime.value = ''
      } finally {
        loading.value = false
      }
    }

    const handlePageChange = async (page) => {
      if (page === currentPage.value) return  // 避免重复搜索
      if (loading.value) return  // 如果正在加载，忽略页面切换
      
      currentPage.value = page
      await performDomainSearch()  // 等待搜索完成
    }

    // 初始化搜索函数
    const initSearch = () => {
      if (loading.value) return  // 如果正在加载，忽略新的搜索请求
      currentPage.value = 1
      performDomainSearch()
    }

    return {
      activeTab,
      username,
      developer,
      developers,
      total,
      currentPage,
      pageSize,
      domainSearch,
      loading,
      searchTime,
      searchByUsername,
      searchByDomain: initSearch,  // 将搜索按钮绑定到初始化搜索函数
      handlePageChange
    }
  }
}
</script>

<style scoped>
.developer-search {
  max-width: 1400px;
  margin: 0 auto;
  padding: 64px 40px;
}

.header {
  text-align: center;
  margin-bottom: 64px;
  max-width: 900px;
  margin-left: auto;
  margin-right: auto;
}

.header h1 {
  color: #37352f;
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 24px;
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.header p {
  color: #787774;
  font-size: 20px;
  line-height: 1.6;
}

.search-card {
  border: none;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin: 0 auto;
  max-width: 1200px;
  padding: 32px;
}

.custom-tabs :deep(.el-tabs__nav) {
  width: 100%;
  display: flex;
  border-bottom: 1px solid #e5e5e5;
}

.custom-tabs :deep(.el-tabs__item) {
  flex: 1;
  text-align: center;
  font-size: 18px;
  padding: 24px 0;
  color: #787774;
  transition: all 0.2s;
}

.custom-tabs :deep(.el-tabs__item.is-active) {
  color: #2eaadc;
  font-weight: 600;
}

.custom-tabs :deep(.el-tabs__active-bar) {
  height: 3px;
  background-color: #2eaadc;
}

.search-container {
  display: flex;
  gap: 20px;
  margin: 48px auto;
  max-width: 800px;
  padding: 0 32px;
}

.search-input {
  flex: 1;
}

.search-input :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #e5e5e5;
  border-radius: 12px;
  transition: all 0.2s;
  padding: 8px 20px;
  height: 56px;
}

.search-input :deep(.el-input__inner) {
  font-size: 18px;
}

.search-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #2eaadc;
}

.search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #2eaadc;
}

.search-container .el-button {
  height: 56px;
  padding: 0 32px;
  font-size: 18px;
  border-radius: 12px;
  min-width: 120px;
}

.domain-form {
  margin: 48px auto;
  max-width: 900px;
  padding: 0 32px;
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.domain-form :deep(.el-form-item) {
  margin-bottom: 0;
  flex: 1;
  min-width: 280px;
}

.domain-form :deep(.el-form-item__label) {
  color: #37352f;
  font-weight: 500;
  font-size: 16px;
  padding-bottom: 12px;
}

.domain-form :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #e5e5e5;
  border-radius: 12px;
  transition: all 0.2s;
  height: 48px;
}

.domain-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #2eaadc;
}

.domain-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #2eaadc;
}

.advanced-options {
  margin: 32px auto;
  max-width: 900px;
  padding: 0 32px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.info-icon {
  color: #787774;
  cursor: pointer;
  transition: color 0.2s;
  font-size: 18px;
}

.info-icon:hover {
  color: #37352f;
}

.loading-state {
  margin: 48px auto;
  max-width: 900px;
  padding: 0 32px;
}

.loading-card {
  border: none;
  background: #f8f9fa;
  border-radius: 16px;
  padding: 32px;
}

.loading-header {
  display: flex;
  align-items: center;
  gap: 16px;
  color: #2eaadc;
  font-weight: 500;
  font-size: 18px;
}

.loading-tip {
  margin-top: 24px;
  color: #787774;
  font-size: 16px;
}

.search-stats {
  margin: 48px auto;
  max-width: 900px;
  padding: 0 32px;
}

.search-stats :deep(.el-alert) {
  border: none;
  background-color: #e8f6fa;
  border-radius: 16px;
  padding: 24px 32px;
}

.search-stats :deep(.el-alert__title) {
  color: #2eaadc;
  font-weight: 500;
  font-size: 16px;
}

.developer-list {
  margin: 48px auto;
  max-width: 1200px;
  padding: 0 32px;
  display: grid;
  gap: 32px;
}

.pagination {
  margin: 48px auto;
  padding: 0 32px;
  display: flex;
  justify-content: center;
}

/* 动画效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

@media (max-width: 768px) {
  .developer-search {
    padding: 40px 20px;
  }

  .header {
    margin-bottom: 40px;
  }

  .header h1 {
    font-size: 36px;
    margin-bottom: 16px;
  }

  .header p {
    font-size: 18px;
  }

  .search-card {
    padding: 20px;
  }

  .search-container {
    flex-direction: column;
    padding: 0 20px;
    margin: 32px auto;
  }

  .search-input :deep(.el-input__wrapper) {
    height: 48px;
  }

  .search-container .el-button {
    height: 48px;
    width: 100%;
  }

  .domain-form {
    flex-direction: column;
    padding: 0 20px;
    margin: 32px auto;
  }

  .domain-form :deep(.el-form-item) {
    width: 100%;
  }

  .advanced-options {
    padding: 0 20px;
  }

  .developer-list {
    padding: 0 20px;
    gap: 24px;
  }
}
</style> 