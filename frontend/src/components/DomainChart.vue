<template>
  <div class="domain-chart">
    <div v-if="!hasData" class="empty">{{ noDataMessage }}</div>
    <div v-else ref="radarRef" class="chart-container"></div>
    <div v-if="hasData" ref="sunburstRef" class="chart-container sunburst"></div>
    <div v-if="hasData" ref="sankeyRef" class="chart-container sankey"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart, SunburstChart, SankeyChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GraphicComponent,
  ToolboxComponent
} from 'echarts/components'
import { LabelLayout } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  RadarChart,
  SunburstChart,
  SankeyChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
  LabelLayout,
  GraphicComponent,
  ToolboxComponent
])

const props = defineProps({
  domains: { type: Array, default: () => [] },
  noDataMessage: { type: String, default: 'No technology domains detected' },
  language: { type: String, default: 'en' }
})

// Translation helper
const t = (key) => {
  const translations = {
    'tech_domains': { en: 'Technology Domains', zh: '技术领域' },
    'radar_title': { en: 'Technology Domain Radar', zh: '技术领域雷达图' },
    'domain_distribution': { en: 'Domain Distribution', zh: '领域分布' },
    'sunburst_title': { en: 'Three-Level Domain Distribution', zh: '三级技术领域分布' },
    'sunburst_subtitle': { en: '(Click inner ring to zoom)', zh: '(点击内环可放大)' },
    'sankey_title': { en: 'Domain Hierarchy Flow (Sankey)', zh: '领域层级流向图 (Sankey)' },
    'score': { en: 'Score', zh: '得分' }
  }
  return translations[key]?.[props.language] || key
}

const flattenData = computed(() =>
  Array.isArray(props.domains)
    ? props.domains.map(d => ({ name: d.name, value: d.score }))
    : []
)
const hasData = computed(() => flattenData.value.length > 0)

const top3Level1 = computed(() =>
  Array.isArray(props.domains)
    ? [...props.domains].sort((a, b) => b.score - a.score).slice(0, 3)
    : []
)

const radarRef = ref(null)
const sunburstRef = ref(null)
const sankeyRef = ref(null)

let radarInstance = null
let sunburstInstance = null
let sankeyInstance = null

// Color palette - professionally designed with better contrast and harmony
const colorPalette = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#4ec9b0'
]

function renderRadar() {
  if (!radarRef.value || !radarInstance || !hasData.value) return
  
  radarInstance.setOption({
    color: colorPalette,
    title: { 
      text: t('radar_title'), 
      left: 'center',
      textStyle: {
        fontSize: 18,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        return `${params.name}: ${params.value}`
      },
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      borderColor: '#ccc',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    radar: {
      indicator: flattenData.value.map(i => ({ name: i.name, max: 100 })),
      shape: 'circle',
      splitNumber: 4,
      axisName: {
        fontSize: 12,
        color: '#555',
        fontWeight: 'bold'
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(255, 255, 255, 0.5)', 'rgba(245, 245, 245, 0.5)']
        }
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#ddd'
        }
      }
    },
    series: [{
      name: t('domain_distribution'),
      type: 'radar',
      data: [{
        value: flattenData.value.map(i => i.value),
        name: t('domain_distribution'),
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          width: 2
        },
        areaStyle: {
          opacity: 0.3
        }
      }]
    }]
  })
}

function toSunburst(nodes = []) {
  return nodes.map(n => ({ 
    name: n.name, 
    value: n.score, 
    itemStyle: { borderRadius: 4 },
    children: n.children ? toSunburst(n.children) : undefined 
  }))
}

function renderSunburst() {
  if (!sunburstRef.value || !sunburstInstance || !hasData.value) return
  
  const data = toSunburst(top3Level1.value)
  
  sunburstInstance.setOption({
    color: colorPalette,
    tooltip: { 
      trigger: 'item', 
      formatter: (params) => `${params.name}<br/>${t('score')}: ${params.value}`,
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      borderColor: '#ccc',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    toolbox: {
      feature: {
        restore: {},
        saveAsImage: {}
      },
      right: 20,
      top: 20
    },
    title: { 
      text: t('sunburst_title'), 
      subtext: t('sunburst_subtitle'), 
      left: 'center', 
      top: 10,
      textStyle: {
        fontSize: 18,
        fontWeight: 'bold'
      },
      subtextStyle: {
        fontSize: 12
      }
    },
    series: [{
      type: 'sunburst', 
      nodeClick: 'zoomToNode', 
      data,
      radius: [60, '90%'], 
      minAngle: 5, 
      sort: undefined,
      emphasis: {
        focus: 'ancestor',
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      },
      label: { 
        rotate: 'radial', 
        overflow: 'truncate', 
        ellipsis: '…', 
        fontSize: 12,
        minAngle: 10,
        color: '#fff'
      },
      itemStyle: {
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.5)'
      },
      levels: [
        {},
        { 
          r0: 60, 
          r: 140, 
          label: { 
            fontSize: 16, 
            fontWeight: 'bold', 
            color: '#fff', 
            rotate: 0,
            backgroundColor: 'rgba(0,0,0,0.3)',
            borderRadius: 4,
            padding: [4, 8]
          },
          itemStyle: {
            borderWidth: 2
          }
        },
        { 
          r0: 140, 
          r: 210, 
          label: { 
            rotate: 'tangential', 
            fontSize: 13,
            color: '#fff'
          } 
        },
        { 
          r0: 210, 
          r: 270, 
          label: { 
            position: 'outside',
            fontSize: 11,
            color: '#333',
            alignTo: 'edge',
            minAngle: 6
          } 
        }
      ]
    }]
  })
}

function toSankey(nodes) {
  const N = [], L = []
  const nodeNameMap = new Map()
  
  const add = (name, lvl) => {
    const id = `${lvl}:${name}`
    if (!N.find(n => n.id === id)) {
      const colorIndex = N.length % colorPalette.length
      N.push({ 
        id, 
        name, 
        itemStyle: { color: colorPalette[colorIndex] },
        label: { 
          formatter: params => {
            const prefixMap = { 'L1': '', 'L2': '', 'L3': '' }
            return prefixMap[lvl] + params.name
          }
        }
      })
      nodeNameMap.set(id, name)
    }
    return id
  }
  
  nodes.forEach(l1 => {
    const id1 = add(l1.name, 'L1')
    l1.children?.forEach(l2 => {
      const id2 = add(l2.name, 'L2')
      L.push({ 
        source: id1, 
        target: id2, 
        value: l2.score,
        lineStyle: { color: 'gradient' }
      })
      l2.children?.forEach(l3 => {
        const id3 = add(l3.name, 'L3')
        L.push({ 
          source: id2, 
          target: id3, 
          value: l3.score,
          lineStyle: { color: 'gradient' }
        })
      })
    })
  })
  
  return { nodes: N, links: L }
}

function renderSankey() {
  if (!sankeyRef.value || !sankeyInstance || !hasData.value) return
  
  const { nodes, links } = toSankey(top3Level1.value)
  
  sankeyInstance.setOption({
    color: colorPalette,
    title: { 
      text: t('sankey_title'), 
      left: 'center', 
      top: 10,
      textStyle: {
        fontSize: 18,
        fontWeight: 'bold'
      }
    },
    tooltip: { 
      trigger: 'item', 
      formatter: p => {
        if (p.dataType === 'edge') {
          return `${p.data.sourceName || p.data.source} ⟶ ${p.data.targetName || p.data.target}<br/>${t('score')}: ${p.data.value}`
        }
        return p.data.name
      },
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      borderColor: '#ccc',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      },
      right: 20,
      top: 20
    },
    series: [{ 
      type: 'sankey', 
      data: nodes, 
      links, 
      emphasis: { 
        focus: 'adjacency',
        lineStyle: {
          width: 5
        }
      }, 
      lineStyle: { 
        color: 'source',
        opacity: 0.6,
        curveness: 0.5
      }, 
      nodeGap: 12, 
      nodeWidth: 24, 
      label: { 
        color: '#333', 
        fontSize: 12,
        fontWeight: 'bold',
        backgroundColor: 'rgba(255, 255, 255, 0.7)',
        padding: [3, 5]
      },
      levels: [
        { depth: 0, itemStyle: { borderColor: '#333', borderWidth: 2 } },
        { depth: 1, itemStyle: { borderColor: '#333', borderWidth: 1 } },
        { depth: 2, itemStyle: { borderColor: '#333', borderWidth: 1 } }
      ],
      layoutIterations: 64
    }]
  })
}

// Resize handler
function handleResize() {
  radarInstance?.resize()
  sunburstInstance?.resize()
  sankeyInstance?.resize()
}

onMounted(async () => {
  await nextTick()
  
  // Initialize charts with responsive options
  if (radarRef.value) {
    radarInstance = echarts.init(radarRef.value)
    renderRadar()
  }
  
  if (sunburstRef.value) {
    sunburstInstance = echarts.init(sunburstRef.value)
    renderSunburst()
  }
  
  if (sankeyRef.value) {
    sankeyInstance = echarts.init(sankeyRef.value)
    renderSankey()
  }
  
  // Add resize listener
  window.addEventListener('resize', handleResize)
  
  // Remove event listener when component is unmounted
  return () => {
    window.removeEventListener('resize', handleResize)
    radarInstance?.dispose()
    sunburstInstance?.dispose()
    sankeyInstance?.dispose()
  }
})

watch(flattenData, () => {
  renderRadar()
  renderSunburst()
  renderSankey()
})
</script>

<style scoped>
.domain-chart {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.chart-container {
  width: 100%;
  height: 400px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  margin-bottom: 32px;
  background: #fff;
}

.sunburst {
  height: 500px;
}

.sankey {
  height: 540px;
}

.empty {
  text-align: center;
  color: #999;
  padding: 3rem 0;
  font-size: 16px;
  background: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}
</style>