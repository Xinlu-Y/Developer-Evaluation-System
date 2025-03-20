import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 600000,  // 增加到 600 秒 (10分钟)
  retry: 5,         // 增加重试次数到5次
  retryDelay: 3000  // 初始重试延迟3秒
})

// 添加请求拦截器
api.interceptors.request.use(
  config => {
    // 对于搜索请求使用更长的超时时间
    if (config.url.includes('/search/domain')) {
      config.timeout = 600000  // 搜索请求使用 600 秒超时
    }
    // 添加重试配置
    config.retry = config.retry || 5
    config.retryDelay = config.retryDelay || 3000
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 添加响应拦截器
api.interceptors.response.use(
  response => response,
  async error => {
    const { config } = error
    
    // 如果配置不存在，或者重试选项没有设置，或者已经重试过了，就直接返回错误
    if (!config || !config.retry || config.__retryCount >= config.retry) {
      console.error('API Error:', {
        url: config?.url,
        method: config?.method,
        status: error.response?.status,
        message: error.message,
        retryCount: config?.__retryCount,
        response: error.response?.data
      })
      return Promise.reject(error)
    }
    
    // 对所有错误类型都进行重试，特别关注连接重置错误
    const shouldRetry = !error.response || 
                       error.code === 'ECONNABORTED' || 
                       error.code === 'ERR_NETWORK' ||
                       error.code === 'ECONNRESET' ||
                       (error.response && (error.response.status >= 500 || error.response.status === 429));
    
    if (!shouldRetry) {
      return Promise.reject(error);
    }
    
    // 设置重试次数
    config.__retryCount = config.__retryCount || 0
    config.__retryCount += 1
    
    // 如果是超时错误或连接重置错误，增加重试延迟
    if (error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK' || error.code === 'ECONNRESET') {
      config.retryDelay = config.retryDelay * 1.5  // 指数退避，但增长慢一些
    }
    
    console.log(`Retrying request (${config.__retryCount}/${config.retry}) after ${config.retryDelay}ms...`, 
                 `Error: ${error.message}`);
    
    // 延迟重试
    await new Promise(resolve => setTimeout(resolve, config.retryDelay))
    
    // 重试请求
    return api(config)
  }
)

export const getDeveloperInfo = (username) => {
  return api.get(`/developer/${username}`)
}

export const getDeveloperSkills = (username, query = '技术能力分析') => {
  return api.get(`/developer/skills/${username}`, { 
    params: { query }
  })
}

export const searchByDomain = (params) => {
  return api.get('/search/domain', { params })
} 