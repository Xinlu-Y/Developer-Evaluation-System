<template>
  <div class="domain-chart">
    <div v-if="!hasLanguageData" class="empty">{{ noDataMessage }}</div>
    <div v-if="hasLanguageData" ref="radarRef" class="chart-container radar"></div>
    <div v-if="hasData" ref="wordcloudRef" class="chart-container wordcloud"></div>
    <div v-if="hasData" ref="sankeyRef" class="chart-container sankey"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart, SankeyChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  ToolboxComponent,
  GraphicComponent,
} from 'echarts/components'
import { LabelLayout } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'
import 'echarts-wordcloud'

echarts.use([
  RadarChart,
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
  languageCharacterStats: { type: Object, default: () => ({}) },
  domains: { type: Array, default: () => [] },
  noDataMessage: { type: String, default: 'No technology domains detected' },
  language: { type: String, default: 'zh' },
  minPercent: { type: Number, default: 0.05 }
})

// Translation helper
const t = (key) => {
  const translations = {
    'tech_domains': { en: 'Technology Domains', zh: '技术领域' },
    'radar_title': { en: ' ', zh: ' ' },
    'language_chars': { en: 'Character Count (bytes)', zh: '字符数 (bytes)' },
    'domain_distribution': { en: 'Domain Distribution', zh: '领域分布' },
    'wordcloud_title': { en: 'Technology Domain Word Cloud', zh: '技术领域词云' },
    'wordcloud_subtitle': { en: '(Size indicates importance)', zh: '(大小表示重要性)' },
    'sankey_title': { en: 'Domain Hierarchy Flow (Sankey)', zh: '领域层级流向图 (Sankey)' },
    'score': { en: 'Score', zh: '得分' },
    'no_language_data': { en: 'No language data available', zh: '没有可用的语言数据' }
  }
  return translations[key]?.[props.language] || key
}

const flattenData = computed(() =>
  Array.isArray(props.domains)
    ? props.domains.map(d => ({ name: d.name, value: d.score }))
    : []
)
const hasData = computed(() => 
  flattenData.value.length > 0
)
const hasLanguageData = computed(() => 
  props.languageCharacterStats && 
  Object.keys(props.languageCharacterStats).length > 0
)
const top3Level1 = computed(() =>
  Array.isArray(props.domains)
    ? [...props.domains].sort((a, b) => b.score - a.score).slice(0, 3)
    : []
)

const radarRef = ref(null)
const wordcloudRef = ref(null)
const sankeyRef = ref(null)

let radarInstance = null
let wordcloudInstance = null
let sankeyInstance = null

const colorPalette = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#4ec9b0'
]

function renderRadar() {
  if (!radarRef.value || !hasLanguageData.value) return

  const existing = echarts.getInstanceByDom(radarRef.value)
  if (existing) existing.dispose()
  radarInstance = echarts.init(radarRef.value)

  const stats = props.languageCharacterStats
  const entries = Object.entries(stats).map(([name, val]) => ({ name, value: val }))
  if (!entries.length) return

  const maxVal    = Math.max(...entries.map(i => i.value))
  const threshold = maxVal * props.minPercent

  let filtered = entries.filter(i => i.value >= threshold)
  if (!filtered.length) {
    const topOne = entries.reduce((p,c) => c.value>p.value?c:p, entries[0])
    filtered = [topOne]
  }
  const labels = filtered.map(i => i.name)
  const values = filtered.map(i => i.value)

  const maxScale = Math.max(...entries.map(i => i.value)) * 1.2

  const option = {
    toolbox: {
      feature: {
        saveAsImage: {}
      },
      right: 20,
      top: 20
    },
    color: colorPalette,
    title: {
      text: t('radar_title'), left: 'left', top: 10,
      textStyle: { fontSize: 18, fontWeight: 'bold' }
    },
    tooltip: {
      show: true,
      trigger: 'item',
      formatter: params => {
        let text = `<strong>${params.seriesName}</strong><br/>`
        params.value.forEach((v,i)=>{
          text += `${labels[i]}: ${v.toLocaleString()}<br/>`
        })
        return text
      }
    },
    radar: {
      shape: 'polygon', 
      splitNumber: 4,
      center: ['50%', '50%'],
      radius: '65%',
      axisLine:  { lineStyle: { color: '#ddd' } },
      splitLine: { lineStyle: { color: '#ddd' } },
      axisName:  { color:'#333', fontSize:14, gap: 10 },
      nameGap: 10,
      indicator: labels.map(name => ({ name, max: maxScale }))
    },
    series: [{
      name: t('language_chars'), type: 'radar',
      data: [{
        value: values, name: t('language_chars'),
        symbol: 'circle', symbolSize: 6,
        lineStyle: { width: 2, color: colorPalette[0] },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: colorPalette[0] },
              { offset: 1, color: 'rgba(255,255,255,0)' }
            ]
          }
        }
      }]
    }]
  }
  radarInstance.setOption(option, { notMerge: true })
}

function toWordCloudData(nodes = []) {
  let data = [];
  
  // Process first level domains
  nodes.forEach(node => {
    data.push({
      name: node.name,
      value: node.score * 10, // Multiply by 10 to make sizes more apparent
      textStyle: {
        color: colorPalette[data.length % colorPalette.length],
        fontWeight: 'bold'
      }
    });
    
    // Process second level domains
    if (node.children && node.children.length) {
      node.children.forEach(child => {
        data.push({
          name: child.name,
          value: child.score * 8, // Slightly smaller than first level
          textStyle: {
            color: colorPalette[(data.length + 2) % colorPalette.length]
          }
        });
        
        // Process third level domains
        if (child.children && child.children.length) {
          child.children.forEach(grandchild => {
            data.push({
              name: grandchild.name,
              value: grandchild.score * 6, // Smaller than second level
              textStyle: {
                color: colorPalette[(data.length + 4) % colorPalette.length],
                fontSize: Math.max(12, grandchild.score / 2)
              }
            });
          });
        }
      });
    }
  });
  
  return data;
}

function renderWordCloud() {
  if (!wordcloudRef.value || !wordcloudInstance || !hasData.value) return
  
  const data = toWordCloudData(top3Level1.value);
  
  wordcloudInstance.setOption({
    color: colorPalette,
    tooltip: { 
      trigger: 'item', 
      formatter: (params) => `${params.name}<br/>${t('score')}: ${params.value / 10}`,
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
    title: { 
      text: t('wordcloud_title'), 
      subtext: t('wordcloud_subtitle'), 
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
      type: 'wordCloud',
      shape: 'circle',
      sizeRange: [12, 60],
      rotationRange: [-45, 45],
      rotationStep: 5,
      gridSize: 8,
      drawOutOfBound: false,
      textStyle: {
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        fontWeight: 'normal',
        color: function() {
          return colorPalette[Math.floor(Math.random() * colorPalette.length)];
        }
      },
      emphasis: {
        textStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.3)'
        }
      },
      data: data
    }]
  });
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
  wordcloudInstance?.resize()
  sankeyInstance?.resize()
}

onMounted(async () => {
  await nextTick()
  
  if (radarRef.value) {
    radarInstance = echarts.init(radarRef.value)
    renderRadar()
  }
  
  if (wordcloudRef.value) {
    wordcloudInstance = echarts.init(wordcloudRef.value)
    renderWordCloud()
  }
  
  if (sankeyRef.value) {
    sankeyInstance = echarts.init(sankeyRef.value)
    renderSankey()
  }
  
  window.addEventListener('resize', handleResize)
  
  return () => {
    window.removeEventListener('resize', handleResize)
    radarInstance?.dispose()
    wordcloudInstance?.dispose()
    sankeyInstance?.dispose()
  }
})

watch(() => [props.languageCharacterStats, props.minPercent], () => {
  renderRadar()
}, { deep: true })

watch(flattenData, () => {
  renderWordCloud()
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

.wordcloud {
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
