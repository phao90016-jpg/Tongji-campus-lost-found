<script setup lang="ts">
// 骨架占位页：v0.1 起替换为真实布局（公共端 + /admin 审核后台）与路由视图。
const project = "校园失物招领与认领审核系统";
const stage = "骨架阶段（第 11 周）：需求仍在评审，前端尚未开工";
</script>

<template>
  <main class="placeholder">
    <h1>{{ project }}</h1>
    <p>{{ stage }}</p>
    <ul>
      <li>接口与状态设计：<code>docs/03-设计.md</code></li>
      <li>业务规则与验收：<code>docs/02-需求.md</code></li>
      <li>当前进度：<code>docs/04-开发与AI.md</code></li>
    </ul>
  </main>
</template>

<style scoped>
.placeholder {
  font-family: system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
  max-width: 720px;
  margin: 12vh auto;
  padding: 0 24px;
  line-height: 1.9;
  color: #242424;
}
h1 {
  font-size: 1.5rem;
}
ul {
  color: #4c5f73;
  font-size: 0.92rem;
}
code {
  background: #f2f5f8;
  padding: 1px 5px;
  border-radius: 4px;
}
</style>
