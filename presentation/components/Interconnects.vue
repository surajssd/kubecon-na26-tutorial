<script setup lang="ts">
const links = [
  { name: 'NVLink', where: 'Dedicated GPU-to-GPU links', width: 100 },
  { name: 'PCIe', where: 'The GPU connection used by our L40s', width: 60 },
  { name: 'RDMA', where: 'Between nodes over InfiniBand or RoCE', width: 55 },
  { name: 'TCP/IP', where: 'Between nodes through the network stack', width: 25 },
]
</script>

<template>
  <figure class="links">
    <figcaption>How GPUs talk <span class="badge simulated">Relative, not to scale</span></figcaption>
    <div v-for="(link, index) in links" :key="link.name" v-click="index + 1" class="link">
      <strong>{{ link.name }}</strong>
      <div class="bar-track"><span class="bar" :style="{ width: `${link.width}%` }" /></div>
      <p>{{ link.where }}</p>
    </div>
  </figure>
</template>

<style scoped>
.links {
  margin: 18px 0 22px;
}

figcaption {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  font-size: 0.8rem;
  font-weight: 700;
}

.link {
  display: grid;
  grid-template-columns: 130px 180px 1fr;
  align-items: center;
  gap: 24px;
  min-height: 52px;
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}

.link strong {
  font-size: 1.05rem;
}

.bar-track {
  height: 12px;
  border-radius: 6px;
  background: rgb(var(--tint) / 0.05);
}

.bar {
  display: block;
  height: 100%;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--req-1), var(--accent));
}

.link p {
  margin: 0;
  font-size: 1rem;
  line-height: 1.4;
}
</style>
