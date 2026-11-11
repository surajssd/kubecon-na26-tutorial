<script setup lang="ts">
import art from '../assets/kubecon/kubecon-na-2026-title-art.png'
import logo from '../assets/kubecon/kubecon-na-2026-logo-white.svg'
</script>

<template>
  <div class="slidev-layout kubecon-title">
    <header class="brand">
      <img class="logo" :src="logo" alt="KubeCon + CloudNativeCon North America 2026">
      <span class="hashtags">#KubeCon #CloudNativeCon</span>
    </header>
    <div class="body">
      <slot />
    </div>
    <div class="art" :style="{ backgroundImage: `url(${art})` }" />
  </div>
</template>

<style scoped>
.kubecon-title {
  display: flex;
  flex-direction: column;
  padding: 0;
  background: var(--brand-blue);
}

.brand {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 22px 34px 0;
}

.logo {
  height: 58px;
}

.hashtags {
  font-size: 0.9rem;
  color: #ffffff;
}

.body {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  padding: 0 34px;
}

/* The KubeCon template crops the right 15.7% of the art, so the bee sits on the slide edge. */
.art {
  height: 226px;
  background-repeat: no-repeat;
  background-position: left bottom;
  background-size: 118.68% auto;
}
</style>
