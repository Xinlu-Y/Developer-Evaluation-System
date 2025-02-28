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
import { Loading } from '@element-plus/icons-vue'

export default {
  name: 'DeveloperSearch',
  components: {
    DeveloperCard,
    Loading
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
      topic: ''
    })

    const searchByUsername = async () => {
      if (!username.value) {
        ElMessage.warning('请输入用户名')
        return
      }
      
      loading.value = true
      try {
        const { data } = await getDeveloperInfo(username.value)
        developer.value = data
      } catch (error) {
        console.error(error)
        ElMessage.error(error.response?.data?.error || '搜索失败')
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
          message: '正在搜索开发者，这可能需要一些时间（最长3分钟）...',
          type: 'info',
          duration: 0
        })
        
        // 显示预计时间提示
        setTimeout(() => {
          if (loading.value) {
            ElMessage({
              message: '搜索仍在进行中，请耐心等待...',
              type: 'info',
              duration: 5000
            })
          }
        }, 30000)  // 30秒后显示提示
        
        const response = await searchByDomainAPI({
          language: domainSearch.language,
          topic: domainSearch.topic,
          offset: (currentPage.value - 1) * pageSize.value,
          limit: pageSize.value
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
        
        if (error.code === 'ECONNABORTED') {
          ElMessage({
            message: '搜索时间过长，请尝试缩小搜索范围或稍后重试',
            type: 'error',
            duration: 5000
          })
        } else if (error.code === 'ERR_NETWORK') {
          ElMessage({
            message: '无法连接到服务器，请检查服务器是否正在运行',
            type: 'error',
            duration: 5000
          })
        } else {
          ElMessage({
            message: error.response?.data?.error || '搜索失败，请稍后重试',
            type: 'error',
            duration: 5000
          })
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  color: #409EFF;
  margin-bottom: 10px;
}

.header p {
  color: #606266;
  font-size: 16px;
}

.search-card {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.custom-tabs :deep(.el-tabs__nav) {
  width: 100%;
  display: flex;
}

.custom-tabs :deep(.el-tabs__item) {
  flex: 1;
  text-align: center;
  font-size: 16px;
}

.search-container {
  display: flex;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  margin-right: 10px;
}

.domain-form {
  margin-bottom: 20px;
}

.developer-list {
  margin-top: 20px;
}

.pagination {
  margin-top: 20px;
  text-align: center;
}

/* 动画效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(30px);
}

/* 添加加载状态相关样式 */
.loading-state {
  margin: 20px 0;
}

.loading-card {
  max-width: 600px;
  margin: 0 auto;
}

.loading-header {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #409EFF;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

.loading-tip {
  margin-top: 10px;
  color: #909399;
  font-size: 14px;
  text-align: center;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 添加搜索统计样式 */
.search-stats {
  margin: 20px 0;
  max-width: 600px;
  margin: 20px auto;
}
</style> 