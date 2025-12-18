<template>
  <div class="container">
    <header class="app-header">
      <h1>🚀 Onyx AI Kurumsal Asistan</h1>
      <p class="subtitle">Verilerinizi ve Belgelerinizi Tek Noktadan Yönetin</p>
    </header>
    
    <div class="mode-selector">
      <button 
        @click="searchMode = 'sql'" 
        :class="{ active: searchMode === 'sql' }"
        class="mode-btn"
      >
        🗄️ Veritabanı Analizi
      </button>
      <button 
        @click="searchMode = 'doc'" 
        :class="{ active: searchMode === 'doc' }"
        class="mode-btn"
      >
        📑 Belge Asistanı
      </button>
    </div>

    <div class="search-box">
      <input 
        v-model="question" 
        @keyup.enter="askQuestion"
        type="text" 
        :placeholder="searchMode === 'sql' ? 'Örn: En çok satış yapan 5 personel kim?' : 'Örn: İade politikasında süre kaç gün?'" 
      />
      <button @click="askQuestion" :disabled="loading" class="ask-btn">
        {{ loading ? 'Düşünüyor...' : 'Sor' }}
      </button>
    </div>

    <div class="upload-section">
      <input type="file" ref="fileInput" @change="handleFileUpload" accept=".pdf,.txt" style="display: none" />
      <button class="upload-btn" @click="$refs.fileInput.click()" :disabled="uploading">
        {{ uploading ? 'Belge Taranıyor...' : '📤 Yeni Belge Yükle (PDF)' }}
      </button>
    </div>

    <div v-if="error" class="error-msg">
      ⚠️ {{ error }}
    </div>

    <div v-if="searchMode === 'doc' && docAnswer" class="ai-summary-card">
      <div class="summary-header">
        <span class="icon">🤖</span>
        <strong>Belge Asistanı Cevabı</strong>
      </div>
      <div class="markdown-content">{{ docAnswer }}</div>
    </div>

    <div v-if="searchMode === 'sql' && summary" class="ai-summary-card">
      <div class="summary-header">
        <span class="icon">✨</span>
        <strong>Yönetici Özeti</strong>
        <button class="pdf-btn" @click="downloadPDF">📥 Rapor İndir</button>
      </div>
      <div class="markdown-content">{{ summary }}</div>
    </div>

    <div v-if="searchMode === 'sql' && resultData && resultData.length > 0" class="results-area">
      
      <div class="view-toggles" v-if="chartData">
        <button @click="viewMode = 'chart'" :class="{ active: viewMode === 'chart' }">📈 Grafik</button>
        <button @click="viewMode = 'table'" :class="{ active: viewMode === 'table' }">📋 Tablo</button>
      </div>

      <div v-if="viewMode === 'chart' && chartData" class="chart-container">
        <component :is="currentChartComponent" :data="chartData" :options="chartOptions" />
      </div>

      <div v-else class="table-container">
        <table>
          <thead>
            <tr>
              <th v-for="(value, key) in resultData[0]" :key="key">{{ formatHeader(key) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in resultData" :key="index">
              <td v-for="(value, key) in row" :key="key">{{ value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="uploadSummary" class="doc-card">
      <div class="doc-header">✅ Belge Başarıyla Eklendi: {{ uploadedFileName }}</div>
      <div>{{ uploadSummary }}</div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, LineElement, ArcElement, PointElement, CategoryScale, LinearScale } from 'chart.js'
import { Bar, Line, Pie } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, ArcElement, PointElement, Title, Tooltip, Legend)

// --- STATE ---
const searchMode = ref('sql') // 'sql' veya 'doc'
const question = ref('')
const loading = ref(false)
const uploading = ref(false)
const error = ref(null)

// SQL Sonuçları
const resultData = ref(null)
const summary = ref(null)
const viewMode = ref('table')

// Belge Sonuçları
const docAnswer = ref(null)
const uploadSummary = ref(null)
const uploadedFileName = ref('')
const fileInput = ref(null)

const detectedChartType = ref('Bar')

// --- ANA FONKSİYON: SORU SOR ---
const askQuestion = async () => {
  if (!question.value) return
  
  loading.value = true
  error.value = null
  
  // Önceki sonuçları temizle
  if(searchMode.value === 'sql') { docAnswer.value = null }
  else { resultData.value = null; summary.value = null }

  try {
    // MODA GÖRE ENDPOINT SEÇİMİ
    const endpoint = searchMode.value === 'sql' 
      ? 'http://127.0.0.1:8000/ask' 
      : 'http://127.0.0.1:8000/ask-doc'

    const response = await axios.post(endpoint, { question: question.value })

    if (response.data.success) {
      if (searchMode.value === 'sql') {
        // SQL Cevabı İşleme
        resultData.value = response.data.data
        summary.value = response.data.summary
        detectChartType(response.data.data)
        if (canRenderChart(response.data.data)) viewMode.value = 'chart'
      } else {
        // Belge Cevabı İşleme
        docAnswer.value = response.data.answer
      }
    } else {
      error.value = "AI Cevap Veremedi: " + (response.data.message || 'Bilinmeyen hata')
    }
  } catch (err) {
    error.value = "Bağlantı Hatası: " + err.message
  } finally {
    loading.value = false
  }
}

// --- DOSYA YÜKLEME ---
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  uploading.value = true
  uploadSummary.value = null
  uploadedFileName.value = file.name
  
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await axios.post('http://127.0.0.1:8000/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (response.data.success) {
      uploadSummary.value = response.data.summary
    } else {
      error.value = "Yükleme Hatası: " + response.data.message
    }
  } catch (err) {
    error.value = "Dosya yüklenemedi."
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

// --- PDF İNDİRME ---
const downloadPDF = async () => {
  if (!summary.value) return
  try {
    const response = await axios.post('http://127.0.0.1:8000/download-pdf', {
      question: question.value,
      summary: summary.value
    }, { responseType: 'blob' })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'Onyx_Rapor.pdf')
    document.body.appendChild(link)
    link.click()
  } catch (err) {
    alert("PDF indirilemedi.")
  }
}

// --- GRAFİK MANTIĞI ---
const detectChartType = (data) => {
  if (!data || data.length === 0) return
  const keys = Object.keys(data[0])
  const hasDate = keys.some(k => k.includes('date') || k.includes('year'))
  if (hasDate) detectedChartType.value = 'Line'
  else if (data.length <= 5) detectedChartType.value = 'Pie'
  else detectedChartType.value = 'Bar'
}

const currentChartComponent = computed(() => {
  if (detectedChartType.value === 'Line') return Line
  if (detectedChartType.value === 'Pie') return Pie
  return Bar
})

const chartData = computed(() => {
  if (!resultData.value || resultData.value.length === 0) return null
  const firstRow = resultData.value[0]
  const keys = Object.keys(firstRow)
  let labelKey = keys.find(k => typeof firstRow[k] === 'string' || k.includes('date')) || keys[0]
  let dataKey = keys.find(k => typeof firstRow[k] === 'number') || keys[1]
  
  // Eğer sayısal veri yoksa grafik çizme
  if (typeof firstRow[dataKey] !== 'number') return null

  const labels = resultData.value.map(row => row[labelKey])
  const bgColors = labels.map(() => `hsl(${Math.random() * 360}, 70%, 50%)`)

  return {
    labels,
    datasets: [{
      label: formatHeader(dataKey),
      backgroundColor: detectedChartType.value === 'Line' ? '#3498db' : bgColors,
      borderColor: '#3498db',
      data: resultData.value.map(row => row[dataKey]),
      tension: 0.1
    }]
  }
})

const chartOptions = computed(() => ({ responsive: true, maintainAspectRatio: false }))
const canRenderChart = (data) => data && data.length > 0 && Object.values(data[0]).some(v => typeof v === 'number')
const formatHeader = (key) => key.replace(/_/g, ' ').toUpperCase()

</script>

<style>
/* GENEL TASARIM */
.container { max-width: 1000px; margin: 0 auto; padding: 20px; font-family: 'Segoe UI', sans-serif; }
.app-header { text-align: center; margin-bottom: 30px; }
.app-header h1 { color: #2c3e50; margin-bottom: 5px; }
.subtitle { color: #7f8c8d; margin-top: 0; }

/* MOD SEÇİCİ */
.mode-selector { display: flex; justify-content: center; gap: 15px; margin-bottom: 20px; }
.mode-btn { 
  padding: 10px 25px; border: 2px solid #ecf0f1; background: white; 
  border-radius: 25px; cursor: pointer; font-weight: bold; color: #95a5a6; transition: 0.3s; 
}
.mode-btn.active { background: #3498db; color: white; border-color: #3498db; box-shadow: 0 4px 10px rgba(52, 152, 219, 0.3); }

/* ARAMA VE BUTONLAR */
.search-box { display: flex; gap: 10px; margin-bottom: 15px; }
input { flex: 1; padding: 15px; border: 2px solid #ecf0f1; border-radius: 10px; font-size: 16px; outline: none; transition: 0.3s; }
input:focus { border-color: #3498db; }
.ask-btn { background: #2c3e50; color: white; padding: 0 30px; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; font-weight: bold; }
.upload-section { text-align: center; margin-bottom: 20px; }
.upload-btn { background: #f39c12; color: white; padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }

/* KARTLAR VE SONUÇLAR */
.ai-summary-card, .doc-card {
  background: white; border-radius: 12px; padding: 25px; margin-bottom: 20px;
  box-shadow: 0 5px 20px rgba(0,0,0,0.05); border-left: 5px solid;
}
.ai-summary-card { border-color: #3498db; } /* Mavi */
.doc-card { border-color: #f39c12; } /* Turuncu */

.summary-header { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; font-size: 1.2rem; color: #2c3e50; }
.markdown-content { white-space: pre-wrap; line-height: 1.6; color: #34495e; }

.error-msg { background: #e74c3c; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; }

/* GRAFİK VE TABLO */
.view-toggles { text-align: center; margin-bottom: 15px; }
.view-toggles button { background: #ecf0f1; border: none; padding: 8px 15px; margin: 0 5px; border-radius: 15px; cursor: pointer; }
.view-toggles button.active { background: #2c3e50; color: white; }
.chart-container { height: 400px; background: white; padding: 15px; border-radius: 12px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 5px 20px rgba(0,0,0,0.05); }
th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ecf0f1; }
th { background: #f8f9fa; font-weight: bold; color: #2c3e50; }

.pdf-btn { margin-left: auto; background: #e74c3c; color: white; border: none; padding: 5px 15px; border-radius: 5px; cursor: pointer; font-size: 0.9rem; }
</style>