<template>
  <div class="domain-chart">
    <div v-if="!hasData" class="empty">{{ noDataMessage }}</div>
    <div v-else ref="chartRef" style="width:100%;height:400px;"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  RadarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer
])

const props = defineProps({
  domains: {
    type: Array,
    default: () => []
  },
  noDataMessage: {
    type: String,
    default: '未能检测到技术领域'
  }
})

// 处理数据
const flattenData = computed(() =>
  Array.isArray(props.domains)
    ? props.domains.map(d => ({ name: d.name, value: d.score }))
    : []
)

const hasData = computed(() => flattenData.value.length > 0)

const chartRef = ref(null)
let chartInstance = null

function renderRadar() {
  if (!chartRef.value || !chartInstance || !hasData.value) return
  chartInstance.setOption({
    title: { text: '技术领域雷达图', left: 'center' },
    tooltip: {},
    radar: {
      indicator: flattenData.value.map(item => ({
        name: item.name,
        max: 100
      }))
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: flattenData.value.map(i => i.value),
            name: '领域分布'
          }
        ]
      }
    ]
  })
}

onMounted(async () => {
  await nextTick() // 确保 DOM 已加载
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value)
    renderRadar()
  }
})

watch(flattenData, () => {
  if (chartInstance) renderRadar()
})
</script>

<style scoped>
.empty {
  text-align: center;
  color: #999;
  padding: 2rem 0;
}
</style>
