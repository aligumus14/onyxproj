<template>
  <div class="ec">
    <div ref="el" class="ec__canvas"></div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  spec: { type: Object, required: true },
})

const el = ref(null)
let chart = null
let ro = null

function cssVar(name, fallback = '') {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

function buildOption(spec) {
  const textColor = cssVar('--text', '#e9edf5')
  const muted = cssVar('--text-muted', 'rgba(233,237,245,.72)')
  const border = cssVar('--border-color', 'rgba(255,255,255,.14)')

  const type = spec?.type || 'bar'
  const dataset = Array.isArray(spec?.dataset) ? spec.dataset : []
  const xKey = spec?.xKey || 'x'
  const seriesSpec = Array.isArray(spec?.series) ? spec.series : []

  const base = {
    backgroundColor: 'transparent',
    textStyle: { color: textColor },
    tooltip: { trigger: type === 'pie' ? 'item' : 'axis' },
    grid: type === 'pie'
      ? undefined
      : { left: 12, right: 12, top: 18, bottom: 12, containLabel: true },
  }

  if (type === 'pie') {
    const nameKey = spec?.nameKey || xKey
    const valueKey = seriesSpec?.[0]?.yKey || spec?.valueKey || 'value'

    return {
      ...base,
      legend: { bottom: 0, textStyle: { color: muted } },
      series: [
        {
          type: 'pie',
          radius: ['35%', '70%'],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: border, borderWidth: 1 },
          label: { color: textColor },
          data: dataset.map((row) => ({
            name: row?.[nameKey],
            value: Number(row?.[valueKey] ?? 0),
          })),
        },
      ],
    }
  }

  const xAxis = {
    type: 'category',
    axisLabel: { color: muted },
    axisLine: { lineStyle: { color: border } },
    axisTick: { show: false },
    data: dataset.map((r) => r?.[xKey]),
  }

  const yAxis = {
    type: 'value',
    axisLabel: { color: muted },
    splitLine: { lineStyle: { color: border, opacity: 0.45 } },
    axisLine: { show: false },
  }

  const stack = !!spec?.stack
  const isArea = type === 'area'

  const series = seriesSpec.length
    ? seriesSpec.map((s) => {
        const chartType =
          type === 'stackedBar' || type === 'bar'
            ? 'bar'
            : 'line'

        const ser = {
          name: s.name || s.yKey,
          type: chartType,
          data: dataset.map((r) => Number(r?.[s.yKey] ?? 0)),
          smooth: chartType === 'line',
          symbol: chartType === 'line' ? 'circle' : undefined,
          symbolSize: chartType === 'line' ? 6 : undefined,
        }

        if (stack && chartType === 'bar') {
          ser.stack = 'total'
        }

        if (isArea && chartType === 'line') {
          ser.areaStyle = {}
        }

        return ser
      })
    : []

  const legend = series.length
    ? { top: 0, textStyle: { color: muted } }
    : undefined

  return {
    ...base,
    legend,
    xAxis,
    yAxis,
    series,
  }
}

function render() {
  if (!chart) return
  const opt = buildOption(props.spec)
  chart.setOption(opt, true)
}

onMounted(() => {
  chart = echarts.init(el.value)
  render()

  ro = new ResizeObserver(() => {
    try {
      chart?.resize()
    } catch {}
  })
  ro.observe(el.value)
})

watch(
  () => props.spec,
  () => render(),
  { deep: true }
)

onBeforeUnmount(() => {
  try {
    ro?.disconnect()
  } catch {}
  ro = null
  try {
    chart?.dispose()
  } catch {}
  chart = null
})
</script>

<style scoped>
.ec{
  width: 100%;
}

.ec__canvas{
  width: 100%;
  height: 280px;
}
</style>
