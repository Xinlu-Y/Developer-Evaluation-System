import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 180000,  // 增加到 180 秒
  retry: 3,         // 增加重试次数
  retryDelay: 5000  // 增加重试延迟到 5 秒
})

// 添加请求拦截器
api.interceptors.request.use(
  config => {
    // 对于搜索请求使用更长的超时时间
    if (config.url.includes('/search/domain')) {
      config.timeout = 300000  // 搜索请求使用 300 秒超时
    }
    // 添加重试配置
    config.retry = config.retry || 3
    config.retryDelay = config.retryDelay || 5000
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
    
    // 如果是超时错误或连接重置错误，增加重试延迟
    if (error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK') {
      config.retryDelay = config.retryDelay * 2  // 指数退避
    }
    
    // 设置重试次数
    config.__retryCount = config.__retryCount || 0
    config.__retryCount += 1
    
    console.log(`Retrying request (${config.__retryCount}/${config.retry}) after ${config.retryDelay}ms...`)
    
    // 延迟重试
    await new Promise(resolve => setTimeout(resolve, config.retryDelay))
    
    // 重试请求
    return api(config)
  }
)

export const getDeveloperInfo = (username) => {
  return api.get(`/developer/${username}`)
}

export const searchByDomain = (params) => {
  return api.get('/search/domain', { params })
} 