import { createRouter, createWebHistory } from "vue-router";

// 骨架期只挂根路由；v0.1 起按角色拆分公共端与 /admin 审核后台路由。
// 需求和设计见 docs/02-需求.md 与 docs/03-设计.md。
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("../App.vue"),
    },
  ],
});

export default router;
