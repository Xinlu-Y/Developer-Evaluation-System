<template>
  <div class="domain-chart">
    <div v-if="!hasData" class="empty">{{ noDataMessage }}</div>
    <div v-else ref="radarRef" style="width:100%;height:400px;"></div>
    <div v-if="hasData" ref="sunburstRef" style="width:100%;height:500px;margin-top:24px;"></div>
    <div v-if="hasData" ref="sankeyRef" style="width:100%;height:520px;margin-top:32px;"></div>
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
  GraphicComponent
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
  GraphicComponent
])

const props = defineProps({
  domains: { type: Array, default: () => [] },
  noDataMessage: { type: String, default: '未能检测到技术领域' }
})

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

function renderRadar() {
  if (!radarRef.value || !radarInstance || !hasData.value) return
  radarInstance.setOption({
    title: { text: '技术领域雷达图', left: 'center' },
    tooltip: {},
    radar: { indicator: flattenData.value.map(i => ({ name: i.name, max: 100 })) },
    series: [{ type: 'radar', data: [{ value: flattenData.value.map(i => i.value), name: '领域分布' }] }]
  })
}

function toSunburst(nodes = []) {
  return nodes.map(n => ({ name: n.name, value: n.score, children: n.children ? toSunburst(n.children) : undefined }))
}

function renderSunburst() {
  if (!sunburstRef.value || !sunburstInstance || !hasData.value) return
  const data = toSunburst(top3Level1.value)
  sunburstInstance.setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>得分：{c}' },
    labelLayout: { hideOverlap: true },
    graphic: { type: 'circle', shape: { r: 28 }, style: { fill: '#fff' } },
    title: { text: '三级技术领域分布', subtext: '(点击内环可放大)', left: 'center', top: 10 },
    series: [{
      type: 'sunburst', nodeClick: 'zoomToNode', data,
      radius: [50, '90%'], minAngle: 4, sort: undefined,
      label: { rotate: 'radial', overflow: 'truncate', ellipsis: '…', fontSize: 11 },
      levels: [
        {},
        { r0: 50, r: 120, label: { fontSize: 14, fontWeight: 'bold', color: '#333', rotate: 0 } },
        { r0: 120, r: 180, label: { rotate: 'tangential', fontSize: 12 } },
        { r0: 180, r: 230, label: { show: false } }
      ],
      colorMappingBy: 'id'
    }]
  })
}

function toSankey(nodes) {
  const N = [], L = []
  const add = (name, lvl) => {
    const id = `${lvl}:${name}`
    if (!N.find(n => n.id === id)) N.push({ id, name })
    return id
  }
  nodes.forEach(l1 => {
    const id1 = add(l1.name, 'L1')
    l1.children?.forEach(l2 => {
      const id2 = add(l2.name, 'L2')
      L.push({ source: id1, target: id2, value: l2.score })
      l2.children?.forEach(l3 => {
        const id3 = add(l3.name, 'L3')
        L.push({ source: id2, target: id3, value: l3.score })
      })
    })
  })
  return { nodes: N, links: L }
}

function renderSankey() {
  if (!sankeyRef.value || !sankeyInstance || !hasData.value) return
  const { nodes, links } = toSankey(top3Level1.value)
  sankeyInstance.setOption({
    title: { text: '领域层级流向图 (Sankey)', left: 'center', top: 10 },
    tooltip: { trigger: 'item', formatter: p => p.dataType === 'edge' ? `${p.data.source} ⟶ ${p.data.target}<br/>得分：${p.data.value}` : p.data.name },
    series: [{ type: 'sankey', data: nodes, links, emphasis: { focus: 'adjacency' }, lineStyle: { opacity: 0.5 }, nodeGap: 14, nodeWidth: 18, label: { color: '#333', fontSize: 11 }, layoutIterations: 0 }]
  })
}

onMounted(async () => {
  await nextTick()
  radarInstance    = radarRef.value    && echarts.init(radarRef.value)
  sunburstInstance = sunburstRef.value && echarts.init(sunburstRef.value)
  sankeyInstance   = sankeyRef.value   && echarts.init(sankeyRef.value)

  renderRadar()
  renderSunburst()
  renderSankey()
})

watch(flattenData, () => {
  renderRadar()
  renderSunburst()
  renderSankey()
})
</script>

<style scoped>
.empty { text-align:center; color:#999; padding:2rem 0; }
</style>
