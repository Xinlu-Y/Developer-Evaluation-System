<template>
  <div class="domain-chart-container">
    <div v-if="hasData" class="chart-wrapper">
      <canvas ref="radarChart"></canvas>
    </div>
    <div v-else class="no-data">
      <p>{{ noDataMessage }}</p>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue'
import Chart from 'chart.js/auto'

export default {
  name: 'DomainChart',
  props: {
    domains: {
      type: Object,
      default: () => ({})
    },
    noDataMessage: {
      type: String,
      default: '暂无领域数据'
    }
  },
  setup(props) {
    const radarChart = ref(null)
    const chartInstance = ref(null)
    
    // 计算是否有数据可供显示
    const hasData = computed(() => {
      return Object.keys(props.domains).length > 0
    })
    
    // 领域名称映射
    const domainNames = {
      'frontend': '前端开发',
      'backend': '后端开发',
      'mobile': '移动开发',
      'data-science': '数据科学',
      'llm': '大语言模型',
      'database': '数据库',
      'devops': 'DevOps',
      'gamedev': '游戏开发',
      'security': '安全',
      'blockchain': '区块链',
      'blockchain': '区块链',
      'systems': '系统编程',
      'graphics': '计算机图形学',
      'computer-vision': '计算机视觉',
      // 'education': '教育和学习',
      'ai': '人工智能',
      'robotics-iot': '机器人和物联网',
      'bioinformatics': '生物信息学',
      'networking': '网络和通信',
      'audio': '音频工程'
    }
    
    // 渲染图表
    const renderChart = () => {
      if (!hasData.value || !radarChart.value) return
      
      // 清除之前的图表实例
      if (chartInstance.value) {
        chartInstance.value.destroy()
      }
      
      // 准备数据
      const labels = []
      const data = []
      
      // 将域名转换为中文，并保持数据同步
      Object.entries(props.domains).forEach(([domain, score]) => {
        const displayName = domainNames[domain] || domain
        labels.push(displayName)
        data.push(score)
      })
      
      // 创建图表
      const ctx = radarChart.value.getContext('2d')
      chartInstance.value = new Chart(ctx, {
        type: 'radar',
        data: {
          labels: labels,
          datasets: [{
            label: '领域分析',
            data: data,
            backgroundColor: 'rgba(64, 158, 255, 0.2)',
            borderColor: 'rgb(64, 158, 255)',
            pointBackgroundColor: 'rgb(64, 158, 255)',
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: 'rgb(64, 158, 255)'
          }]
        },
        options: {
          scales: {
            r: {
              angleLines: {
                display: true
              },
              suggestedMin: 0,
              suggestedMax: 100
            }
          },
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return `分数: ${context.raw.toFixed(1)}`;
                }
              }
            }
          },
          maintainAspectRatio: false
        }
      })
    }
    
    // 监听数据变化重新渲染
    watch(() => props.domains, () => {
      renderChart()
    }, { deep: true })
    
    // 组件挂载后初始化图表
    onMounted(() => {
      if (hasData.value) {
        renderChart()
      }
    })
    
    return {
      radarChart,
      hasData,
      noDataMessage: props.noDataMessage
    }
  }
}
</script>

<style scoped>
.domain-chart-container {
  width: 100%;
  height: 300px;
  position: relative;
}

.chart-wrapper {
  width: 100%;
  height: 100%;
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  font-size: 14px;
  text-align: center;
  background-color: #f5f7fa;
  border-radius: 4px;
}
</style> 