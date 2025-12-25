<template>
  <div class="lp">
    <div class="lp__card">
      <div class="lp__brand">
        <div class="lp__logo">Onyx</div>
        <div class="lp__tag">BI Chat • SQL + Doküman Asistanı</div>
      </div>

      <form class="lp__form" @submit.prevent="submit">
        <label class="lp__label">E-posta</label>
        <input
          v-model="email"
          class="input lp__input"
          type="email"
          autocomplete="username"
          placeholder="ali@company.com"
        />

        <label class="lp__label">Şifre</label>
        <input
          v-model="password"
          class="input lp__input"
          type="password"
          autocomplete="current-password"
          placeholder="••••••••"
        />

        <div class="lp__row">
          <label class="lp__check">
            <input type="checkbox" v-model="remember" />
            <span>Beni hatırla</span>
          </label>

          <button class="btn btn-primary lp__btn" type="submit" :disabled="loading">
            {{ loading ? '...' : 'Giriş' }}
          </button>
        </div>

        <div v-if="err" class="lp__error">⚠️ {{ err }}</div>

        <div class="lp__hint">
          Şimdilik token localStorage’a yazılıyor. İstersen bir sonraki adımda backend auth endpoint’ine bağlarız.
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const email = ref('')
const password = ref('')
const remember = ref(true)
const loading = ref(false)
const err = ref('')

async function submit() {
  err.value = ''
  if (!email.value.trim() || !password.value.trim()) {
    err.value = 'E-posta ve şifre gerekli.'
    return
  }

  loading.value = true
  try {
    // şimdilik demo token
    const token = 'onyx-demo-token'
    localStorage.setItem('onyx_token', token)
    localStorage.setItem(
      'onyx_user',
      JSON.stringify({
        name: email.value.split('@')[0] || 'User',
        email: email.value.trim(),
      })
    )

    router.push('/app')
  } catch (e) {
    err.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}
</script>


<style scoped>
.lp{
  height: 100%;
  display:flex;
  align-items:center;
  justify-content:center;
  padding: 18px;
  background:
    radial-gradient(1200px 500px at 20% 10%, rgba(109,94,252,.18), transparent 60%),
    radial-gradient(900px 420px at 80% 20%, rgba(0,180,255,.12), transparent 60%),
    var(--bg-app);
}

.lp__card{
  width: min(460px, 96vw);
  border-radius: 18px;
  border: 1px solid var(--border-color);
  background: var(--bg-sidebar);
  box-shadow: 0 30px 80px rgba(0,0,0,.35);
  padding: 18px;
}

.lp__brand{
  margin-bottom: 14px;
}

.lp__logo{
  font-weight: 950;
  letter-spacing: .3px;
  color: var(--text);
  font-size: 22px;
}

.lp__tag{
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.lp__form{
  display:flex;
  flex-direction: column;
  gap: 10px;
}

.lp__label{
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 850;
  margin-top: 6px;
}

.lp__input{
  height: 40px;
  border-radius: 14px;
}

.lp__row{
  margin-top: 10px;
  display:flex;
  align-items:center;
  justify-content: space-between;
  gap: 10px;
}

.lp__check{
  display:flex;
  align-items:center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 12px;
  user-select: none;
}

.lp__btn{
  height: 40px;
  border-radius: 14px;
  padding: 0 16px;
}

.lp__error{
  margin-top: 6px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(255, 76, 76, .35);
  background: rgba(255, 76, 76, .12);
  color: var(--text);
  font-size: 12px;
}

.lp__hint{
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.4;
}
</style>
