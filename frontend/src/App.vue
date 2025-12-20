<template>
  <div class="container">
    <header class="app-header">
      <h1>🚀 Onyx AI Kurumsal Asistan</h1>
      <p class="subtitle">Verilerinizi ve Belgelerinizi Tek Noktadan Yönetin</p>
    </header>

    <div class="mode-selector">
      <button @click="setMode('sql')" :class="{ active: searchMode === 'sql' }" class="mode-btn">
        🗄️ Veritabanı Analizi
      </button>
      <button @click="setMode('doc')" :class="{ active: searchMode === 'doc' }" class="mode-btn">
        📑 Belge Asistanı
      </button>
    </div>

    <div class="search-box">
      <input
        v-model="question"
        @keyup.enter="askQuestion"
        type="text"
        :placeholder="searchMode === 'sql'
          ? 'Örn: En çok satış yapan 5 personel kim?'
          : 'Örn: Palet Sarma Makinesi için yapılan işlemleri maddeler halinde yaz.'"
      />
      <button @click="askQuestion" :disabled="loading" class="ask-btn">
        {{ loading ? 'Düşünüyor...' : 'Sor' }}
      </button>
    </div>

    <div class="upload-section">
      <input
        type="file"
        ref="fileInput"
        @change="handleFileUpload"
        accept=".pdf,.txt"
        style="display:none"
      />
      <button class="upload-btn" @click="$refs.fileInput.click()" :disabled="uploading">
        {{ uploading ? 'Belge Taranıyor...' : '📤 Yeni Belge Yükle (PDF)' }}
      </button>
    </div>

    <div v-if="error" class="error-msg">
      ⚠️ {{ error }}
    </div>

    <!-- DOC ANSWER -->
    <div v-if="searchMode === 'doc' && docAnswer" class="ai-summary-card">
      <div class="summary-header">
        <span class="icon">🤖</span>
        <strong>Belge Asistanı Cevabı</strong>

        <span v-if="docMode" class="pill">Mode: {{ docMode }}</span>
        <span v-if="docSelectedId" class="pill pill--accent" title="Seçilen belge">
          Seçilen: {{ docSelectedId }}
        </span>
      </div>

      <div class="markdown-content">{{ docAnswer }}</div>
    </div>

    <!-- DOC CANDIDATES -->
    <div v-if="searchMode === 'doc' && docCandidates.length" class="doc-candidates-card">
      <div class="summary-header summary-header--small">
        <span class="icon">📌</span>
        <strong>Bu cevap için bakılan belgeler</strong>
        <span class="muted" style="margin-left:auto">{{ docCandidates.length }} aday</span>
      </div>

      <div class="candidate-list">
        <div
          v-for="c in docCandidates"
          :key="c.doc_id"
          class="candidate-item"
          :class="{ 'candidate-item--selected': c.doc_id === docSelectedId }"
        >
          <div class="candidate-top">
            <div class="candidate-main">
              <strong class="docid">{{ c.doc_id }}</strong>
              <span class="badge">{{ c.doc_type || '-' }}</span>
              <span class="muted">Score: {{ formatScore(c.score) }}</span>
            </div>

            <div class="candidate-actions">
              <button class="mini-btn" @click="copyText(c.doc_id)">Kopyala</button>
              <button class="mini-btn" @click="openDocModal(c.doc_id)">Belgeyi Gör</button>
              <button class="mini-btn mini-btn--primary" @click="askWithId(c.doc_id)">
                Bu ID ile tekrar sor
              </button>
            </div>
          </div>

          <div class="candidate-sub muted">
            <span v-if="c.date">Tarih: {{ c.date }}</span>
            <span v-if="c.vendor"> | Tedarikçi: {{ c.vendor }}</span>
            <span v-if="c.machine"> | Makine: {{ c.machine }}</span>
            <span v-if="c.grand_total != null"> | Genel Toplam: {{ c.grand_total }}</span>
          </div>
        </div>
      </div>

      <div class="hint muted">
        İpucu: “Belgeyi Gör” ile içeriği aç, “Bu ID ile tekrar sor” ile tek belgeyi hedefle.
      </div>
    </div>

    <!-- SQL SUMMARY -->
    <div v-if="searchMode === 'sql' && summary" class="ai-summary-card">
      <div class="summary-header">
        <span class="icon">✨</span>
        <strong>Yönetici Özeti</strong>
        <button class="pdf-btn" @click="downloadPDF">📥 Rapor İndir</button>
      </div>
      <div class="markdown-content">{{ summary }}</div>
    </div>

    <!-- SQL RESULTS -->
    <div v-if="searchMode === 'sql' && resultData" class="results-area">
      <!-- ✅ 0 satır: artık boş kalmayacak -->
      <div v-if="Array.isArray(resultData) && resultData.length === 0" class="empty-state">
        Bu sorgu 0 satır döndürdü. (Filtre/tarih veride olmayabilir.)
      </div>

      <!-- ✅ Satır varsa: mevcut akışın -->
      <template v-else>
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
                <th v-for="(value, key) in resultData[0]" :key="key">
                  {{ formatHeader(key) }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in resultData" :key="index">
                <td v-for="(value, key) in row" :key="key">{{ formatCell(value, key) }}</td>

              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>


    <!-- UPLOAD SUMMARY -->
    <div v-if="uploadSummary" class="doc-card">
      <div class="doc-header">✅ Belge Başarıyla Eklendi: {{ uploadedFileName }}</div>
      <div>{{ uploadSummary }}</div>
    </div>

    <!-- ========================= -->
    <!-- DOCUMENT MODAL / DRAWER -->
    <!-- ========================= -->
    <div v-if="docModalOpen" class="modal-overlay" @click.self="closeDocModal">
      <div class="modal-drawer" role="dialog" aria-modal="true">
        <div class="modal-header">
          <div class="modal-title">
            <strong>📄 Belge Görüntüleyici</strong>
            <div class="modal-sub muted">
              <span v-if="docModalDocId">ID: {{ docModalDocId }}</span>
              <span v-if="docModalType"> | Tür: {{ docModalType }}</span>
            </div>
          </div>

          <div class="modal-actions">
            <button class="mini-btn" @click="closeDocModal">Kapat</button>
          </div>
        </div>

        <div class="modal-tabs">
          <button
            class="tab-btn"
            :class="{ active: docModalTab === 'view' }"
            @click="docModalTab = 'view'"
          >
            Özet Görünüm
          </button>
          <button
            class="tab-btn"
            :class="{ active: docModalTab === 'json' }"
            @click="docModalTab = 'json'"
          >
            Ham JSON
          </button>
        </div>

        <div class="modal-body">
          <div v-if="docModalLoading" class="muted">Yükleniyor...</div>
          <div v-else-if="docModalError" class="error-in-modal">
            ⚠️ {{ docModalError }}
          </div>
          <div v-else-if="!docModalDocument" class="muted">
            Belge bulunamadı.
          </div>

          <!-- VIEW TAB -->
          <div v-else-if="docModalTab === 'view'">
            <!-- INVOICE -->
            <div v-if="docModalType === 'invoice'">
              <div class="kv-grid">
                <div class="kv"><span class="k">Tedarikçi</span><span class="v">{{ docModalDocument.vendor || '-' }}</span></div>
                <div class="kv"><span class="k">Tarih</span><span class="v">{{ docModalDocument.date || '-' }}</span></div>
                <div class="kv"><span class="k">Belge No</span><span class="v">{{ docModalDocument.invoice_no || docModalDocument.doc_id || '-' }}</span></div>
              </div>

              <div class="section-title">Kalemler</div>
              <div class="table-container modal-table">
                <table>
                  <thead>
                    <tr>
                      <th>Ürün</th>
                      <th>Adet</th>
                      <th>Birim</th>
                      <th>Birim Fiyat</th>
                      <th>Satır Toplam</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(it, idx) in (docModalDocument.items || [])" :key="idx">
                      <td>{{ it.product || it.name || '-' }}</td>
                      <td>{{ it.quantity ?? '-' }}</td>
                      <td>{{ it.unit || '-' }}</td>
                      <td>{{ fmtMoney(it.unit_price) }}</td>
                      <td>{{ fmtMoney(it.line_total ?? it.total ?? it.net_total) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div class="totals">
                <div class="tot-row">
                  <span>Ara Toplam</span>
                  <strong>{{ fmtMoney(docModalDocument.subtotal ?? docModalDocument.net_total) }}</strong>
                </div>
                <div class="tot-row">
                  <span>KDV</span>
                  <strong>{{ fmtMoney(docModalDocument.tax_total ?? docModalDocument.vat_total) }}</strong>
                </div>
                <div class="tot-row tot-row--grand">
                  <span>Genel Toplam</span>
                  <strong>{{ fmtMoney(docModalDocument.grand_total ?? docModalDocument.total) }}</strong>
                </div>
              </div>
            </div>

            <!-- SERVICE REPORT -->
            <div v-else-if="docModalType === 'service_report'">
              <div class="kv-grid">
                <div class="kv"><span class="k">Makine</span><span class="v">{{ docModalDocument.machine || '-' }}</span></div>
                <div class="kv"><span class="k">Tarih</span><span class="v">{{ docModalDocument.date || '-' }}</span></div>
                <div class="kv"><span class="k">Rapor No</span><span class="v">{{ docModalDocument.doc_id || '-' }}</span></div>
              </div>

              <div class="section-title">Arıza / Şikayet</div>
              <div class="box">
                {{ docModalDocument.fault_description || docModalDocument.issue || '-' }}
              </div>

              <div class="section-title">Yapılan İşlemler</div>
              <ul class="bullets">
                <li v-for="(a, idx) in normalizeActions(docModalDocument.actions)" :key="idx">
                  {{ a }}
                </li>
              </ul>
            </div>

            <!-- HR LETTER -->
            <div v-else-if="docModalType === 'hr_letter'">
              <div class="kv-grid">
                <div class="kv"><span class="k">Tarih</span><span class="v">{{ docModalDocument.date || '-' }}</span></div>
                <div class="kv"><span class="k">Konu</span><span class="v">{{ docModalDocument.subject || '-' }}</span></div>
                <div class="kv"><span class="k">Tür</span><span class="v">{{ docModalDocument.letter_type || '-' }}</span></div>
              </div>

              <div class="section-title">Metin</div>
              <div class="box">
                {{ docModalDocument.body || docModalDocument.text || '-' }}
              </div>
            </div>

            <!-- FALLBACK -->
            <div v-else>
              <div class="muted">Bu belge türü için özel görünüm yok. Ham JSON sekmesinden görüntüleyebilirsin.</div>
            </div>
          </div>

          <!-- JSON TAB -->
          <div v-else>
            <pre class="json-pre">{{ prettyJson(docModalDocument) }}</pre>
          </div>
        </div>
      </div>
    </div>
    <!-- END MODAL -->
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  LineElement,
  ArcElement,
  PointElement,
  CategoryScale,
  LinearScale
} from 'chart.js'
import { Bar, Line, Pie } from 'vue-chartjs'

ChartJS.register(
  CategoryScale, LinearScale,
  BarElement, LineElement, ArcElement, PointElement,
  Title, Tooltip, Legend
)

const API_BASE = 'http://127.0.0.1:8000'

// STATE
const searchMode = ref('sql')
const question = ref('')
const loading = ref(false)
const uploading = ref(false)
const error = ref(null)

// SQL
const resultData = ref(null)
const summary = ref(null)
const viewMode = ref('table')
const detectedChartType = ref('Bar')

// DOC
const docAnswer = ref(null)
const docMode = ref(null)
const docSelectedId = ref(null)
const docCandidates = ref([])

// UPLOAD
const uploadSummary = ref(null)
const uploadedFileName = ref('')
const fileInput = ref(null)

// MODAL (Document Viewer)
const docModalOpen = ref(false)
const docModalLoading = ref(false)
const docModalError = ref(null)
const docModalDocId = ref(null)
const docModalType = ref(null)
const docModalDocument = ref(null)
const docModalTab = ref('view')

const setMode = (mode) => {
  searchMode.value = mode
  error.value = null

  if (mode === 'sql') {
    docAnswer.value = null
    docMode.value = null
    docSelectedId.value = null
    docCandidates.value = []
  } else {
    resultData.value = null
    summary.value = null
  }
}

const formatScore = (s) => {
  if (s === null || s === undefined || s === '') return '-'
  const n = Number(s)
  if (Number.isFinite(n)) return n.toFixed(2)
  return String(s)
}


const copyText = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const el = document.createElement('textarea')
    el.value = text
    document.body.appendChild(el)
    el.select()
    document.execCommand('copy')
    document.body.removeChild(el)
  }
}

const askWithId = async (docId) => {
  if (!docId) return
  const baseQ = question.value?.trim() || ''
  const hasIdAlready = /^([A-Z]{2,3}-\d{4}-\d{6})\b/.test(baseQ)
  question.value = hasIdAlready ? baseQ : `${docId} ${baseQ}`.trim()
  await askQuestion()
}

const askQuestion = async () => {
  if (!question.value?.trim()) return

  loading.value = true
  error.value = null

  if (searchMode.value === 'sql') {
    docAnswer.value = null
    docMode.value = null
    docSelectedId.value = null
    docCandidates.value = []
  } else {
    resultData.value = null
    summary.value = null
  }

  try {
    const endpoint = searchMode.value === 'sql'
      ? `${API_BASE}/ask`
      : `${API_BASE}/ask-doc`

    const response = await axios.post(endpoint, { question: question.value })

    if (!response.data?.success) {
      error.value = "AI Cevap Veremedi: " + (response.data?.message || 'Bilinmeyen hata')
      return
    }

    if (searchMode.value === 'sql') {
      resultData.value = response.data.data
      summary.value = response.data.summary
      detectChartType(response.data.data)
      if (canRenderChart(response.data.data)) viewMode.value = 'chart'
    } else {
      docAnswer.value = response.data.answer
      docMode.value = response.data.mode ?? null
      docSelectedId.value = response.data.selected_doc_id ?? null
      docCandidates.value = Array.isArray(response.data.candidates) ? response.data.candidates : []
    }
  } catch (err) {
    error.value = "Bağlantı Hatası: " + (err?.message || 'Bilinmeyen hata')
  } finally {
    loading.value = false
  }
}

// Upload
const handleFileUpload = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  uploading.value = true
  uploadSummary.value = null
  uploadedFileName.value = file.name

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await axios.post(`${API_BASE}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    if (response.data?.success) {
      uploadSummary.value = response.data.summary
    } else {
      error.value = "Yükleme Hatası: " + (response.data?.message || 'Bilinmeyen hata')
    }
  } catch (err) {
    error.value = "Dosya yüklenemedi."
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

// PDF
const downloadPDF = async () => {
  if (!summary.value) return
  try {
    const response = await axios.post(`${API_BASE}/download-pdf`, {
      question: question.value,
      summary: summary.value
    }, { responseType: 'blob' })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'Onyx_Rapor.pdf')
    document.body.appendChild(link)
    link.click()
  } catch {
    alert("PDF indirilemedi.")
  }
}

// ========= MODAL LOGIC =========
const openDocModal = async (docId) => {
  docModalOpen.value = true
  docModalLoading.value = true
  docModalError.value = null
  docModalDocId.value = docId
  docModalDocument.value = null
  docModalType.value = null
  docModalTab.value = 'view'

  try {
    const res = await axios.get(`${API_BASE}/document/${encodeURIComponent(docId)}`)
    if (!res.data?.success) {
      docModalError.value = res.data?.message || 'Belge alınamadı.'
      return
    }
    docModalDocument.value = res.data.document || null
    docModalType.value = res.data.doc_type || (res.data.document?.doc_type ?? null)
  } catch (e) {
    docModalError.value = e?.response?.data?.detail || e?.message || 'Belge alınamadı.'
  } finally {
    docModalLoading.value = false
  }
}

const closeDocModal = () => {
  docModalOpen.value = false
}

const prettyJson = (obj) => {
  try { return JSON.stringify(obj, null, 2) } catch { return String(obj) }
}

const fmtMoney = (v) => {
  if (v == null || v === '') return '-'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  // TL formatı basit
  return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(n)
}

const normalizeActions = (actions) => {
  if (!actions) return []
  if (Array.isArray(actions)) return actions.map(x => String(x)).filter(Boolean)
  // bazen tek string gelebilir
  return String(actions)
    .split(/\r?\n|•|- /)
    .map(s => s.trim())
    .filter(Boolean)
}

// Charts
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
  const labelKey = keys.find(k => typeof firstRow[k] === 'string' || k.includes('date')) || keys[0]
  const dataKey = keys.find(k => typeof firstRow[k] === 'number') || keys[1]
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
const isMoneyKey = (key) => {
  const k = String(key || '').toLowerCase()
  return (
    k.includes('total') ||
    k.includes('sales') ||
    k.includes('amount') ||
    k.includes('revenue') ||
    k.includes('grand') ||
    k.includes('price') ||
    k.includes('cost')
  )
}

const formatCell = (value, key) => {
  if (value === null || value === undefined || value === '') return '-'

  // money-like fields -> 2 decimals + tr-TR formatting
  if (isMoneyKey(key) && typeof value === 'number') {
    return new Intl.NumberFormat('tr-TR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  // generic numbers
  if (typeof value === 'number') {
    return new Intl.NumberFormat('tr-TR').format(value)
  }

  return value
}

</script>

<style>
/* GENEL */
.container { max-width: 1000px; margin: 0 auto; padding: 20px; font-family: 'Segoe UI', sans-serif; }
.app-header { text-align: center; margin-bottom: 30px; }
.app-header h1 { color: #2c3e50; margin-bottom: 5px; }
.subtitle { color: #7f8c8d; margin-top: 0; }

/* MOD */
.mode-selector { display: flex; justify-content: center; gap: 15px; margin-bottom: 20px; }
.mode-btn {
  padding: 10px 25px; border: 2px solid #ecf0f1; background: white;
  border-radius: 25px; cursor: pointer; font-weight: bold; color: #95a5a6; transition: 0.3s;
}
.mode-btn.active { background: #3498db; color: white; border-color: #3498db; box-shadow: 0 4px 10px rgba(52, 152, 219, 0.3); }

/* SEARCH */
.search-box { display: flex; gap: 10px; margin-bottom: 15px; }
input {
  flex: 1; padding: 15px; border: 2px solid #ecf0f1; border-radius: 10px;
  font-size: 16px; outline: none; transition: 0.3s;
}
input:focus { border-color: #3498db; }
.ask-btn { background: #2c3e50; color: white; padding: 0 30px; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; font-weight: bold; }

.upload-section { text-align: center; margin-bottom: 20px; }
.upload-btn { background: #f39c12; color: white; padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }

.error-msg { background: #e74c3c; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; }

/* KART */
.ai-summary-card, .doc-card {
  background: white; border-radius: 12px; padding: 25px; margin-bottom: 20px;
  box-shadow: 0 5px 20px rgba(0,0,0,0.05); border-left: 5px solid;
}
.ai-summary-card { border-color: #3498db; }
.doc-card { border-color: #f39c12; }

.summary-header { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; font-size: 1.2rem; color: #2c3e50; }
.summary-header--small { font-size: 1.05rem; margin-bottom: 10px; }
.markdown-content { white-space: pre-wrap; line-height: 1.6; color: #34495e; }

.pdf-btn { margin-left: auto; background: #e74c3c; color: white; border: none; padding: 5px 15px; border-radius: 5px; cursor: pointer; font-size: 0.9rem; }

.pill{
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f2f6ff;
  color: #2c3e50;
  border: 1px solid rgba(52,152,219,.15);
}
.pill--accent{
  background:#fff7ed;
  border-color: rgba(243,156,18,.25);
}

/* DOC candidates */
.doc-candidates-card{
  background: white;
  border-radius: 12px;
  padding: 18px;
  margin-bottom: 20px;
  box-shadow: 0 5px 20px rgba(0,0,0,0.05);
  border-left: 5px solid #9b59b6;
}
.candidate-list{ display:flex; flex-direction:column; gap:12px; }
.candidate-item{ border: 1px solid #ecf0f1; border-radius: 12px; padding: 12px; }
.candidate-item--selected{ border-color: rgba(52,152,219,.45); box-shadow: 0 0 0 3px rgba(52,152,219,.08); }
.candidate-top{ display:flex; align-items:flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.candidate-main{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.docid{ color:#2c3e50; }
.badge{ font-size: 12px; padding: 2px 8px; border: 1px solid #ecf0f1; border-radius: 999px; color:#2c3e50; background:#f8f9fa; }
.candidate-actions{ display:flex; gap:8px; flex-wrap:wrap; }
.mini-btn{
  border: 1px solid #ecf0f1;
  background: #ffffff;
  color: #2c3e50;
  padding: 6px 10px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
}
.mini-btn--primary{ background: #3498db; border-color: #3498db; color: white; }
.candidate-sub{ margin-top: 6px; }
.muted{ opacity: .75; font-size: 13px; color: #2c3e50; }
.hint{ margin-top: 10px; }

/* MODAL / DRAWER */
.modal-overlay{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.45);
  display: flex;
  justify-content: flex-end;
  z-index: 9999;
}
.modal-drawer{
  width: min(520px, 92vw);
  height: 100%;
  background: #ffffff;
  box-shadow: -10px 0 30px rgba(0,0,0,.25);
  display: flex;
  flex-direction: column;
}
.modal-header{
  padding: 14px 14px 10px;
  border-bottom: 1px solid #ecf0f1;
  display:flex;
  align-items:flex-start;
  justify-content: space-between;
  gap: 12px;
}
.modal-sub{ margin-top: 4px; }
.modal-tabs{
  display:flex;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid #ecf0f1;
}
.tab-btn{
  border: 1px solid #ecf0f1;
  background: #fff;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
}
.tab-btn.active{
  border-color: rgba(52,152,219,.35);
  box-shadow: 0 0 0 3px rgba(52,152,219,.08);
}
.modal-body{
  padding: 14px;
  overflow: auto;
  flex: 1;
}
.error-in-modal{
  background: #fdecec;
  border: 1px solid #f5c2c2;
  padding: 10px;
  border-radius: 10px;
  color: #8a1f1f;
}

/* Viewer UI */
.section-title{
  margin: 14px 0 8px;
  font-weight: 700;
  color: #2c3e50;
}
.kv-grid{
  display:grid;
  grid-template-columns: 1fr;
  gap: 8px;
}
.kv{
  display:flex;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #ecf0f1;
  border-radius: 10px;
  padding: 10px;
  background: #fafafa;
}
.k{ opacity:.8; }
.v{ font-weight: 600; }

.box{
  border: 1px solid #ecf0f1;
  border-radius: 12px;
  padding: 10px;
  background: #fafafa;
  white-space: pre-wrap;
}

.bullets{
  margin: 0;
  padding-left: 18px;
}
.bullets li{ margin-bottom: 6px; }

.modal-table{ margin-top: 8px; }
.table-container table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 5px 20px rgba(0,0,0,0.05); }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }
th { background: #f8f9fa; font-weight: bold; color: #2c3e50; }

.totals{
  margin-top: 12px;
  border: 1px solid #ecf0f1;
  border-radius: 12px;
  overflow:hidden;
}
.tot-row{
  display:flex;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #ecf0f1;
  background: #fff;
}
.tot-row--grand{
  background: #f2f6ff;
  border-bottom: none;
}
.json-pre{
  font-size: 12px;
  line-height: 1.5;
  background: #0b1020;
  color: #e6edf3;
  padding: 12px;
  border-radius: 12px;
  overflow: auto;
}
.ai-summary-card,
.doc-candidates-card,
.doc-card,
.candidate-item,
.modal-drawer {
  color: #0f172a;
}

.ai-summary-card .muted,
.doc-candidates-card .muted,
.candidate-item .muted,
.modal-drawer .muted {
  color: #475569;
  opacity: 1;
}

/* Buttons/tabs inside modal */
.modal-drawer .tab-btn { color: #0f172a; }
.modal-drawer .badge { color: #0f172a; }

/* JSON view already uses dark theme */
.modal-drawer .json-pre { color: #e6edf3; }
</style>
