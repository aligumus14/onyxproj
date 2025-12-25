<template>
  <div class="shell">
    <aside class="shell__sidebar">
      <slot name="sidebar" />
    </aside>

    <header class="shell__topbar">
      <slot name="topbar" />
    </header>

    <main class="shell__main">
      <section class="shell__chat">
        <slot name="chat" />
      </section>

      <section class="shell__results">
        <slot name="results" />
      </section>
    </main>

    <slot name="modal" />
  </div>
</template>

<script setup>
/* slots only */
</script>

<style scoped>
.shell{
  height: 100%;
  width: 100%;
  display: grid;

  /* ✅ Collapse burada çalışır: */
  grid-template-columns: var(--sidebar-width, 320px) minmax(0, 1fr);
  grid-template-rows: 56px minmax(0, 1fr);
  grid-template-areas:
    "sidebar topbar"
    "sidebar main";

  background: var(--bg-app);
}

/* ✅ Sidebar sütunu: taşma ve min-width kilitlerini kırıyoruz */
.shell__sidebar{
  grid-area: sidebar;
  min-width: 0;
  overflow: hidden;
  border-right: 1px solid var(--border-color);
  background: var(--bg-sidebar);
}

/* topbar */
.shell__topbar{
  grid-area: topbar;
  min-width: 0;
  display:flex;
  align-items:center;
  padding: 10px 12px;
  background: var(--bg-topbar);
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(6px);
}

/* main: chat + results */
.shell__main{
  grid-area: main;
  min-width: 0;
  min-height: 0;
  display:grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 460px);
  gap: 14px;
  padding: 14px;
  overflow: hidden;
}

.shell__chat,
.shell__results{
  min-width: 0;
  min-height: 0;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  background: rgba(255,255,255,.03);
  padding: 12px;
  overflow: hidden;
}

/* responsive */
@media (max-width: 1100px){
  .shell__main{
    grid-template-columns: 1fr;
  }
  .shell__results{
    display:none; /* mobil/tablet: sonuç panelini sonra ayrı açarız */
  }
}
</style>
