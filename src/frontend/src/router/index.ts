import { createRouter, createWebHistory } from "vue-router";

// 骨架期只挂根路由；v0.1 起按角色拆分公共端与 /admin 审核后台路由，
// 页面与用例的对照见 src/frontend/README.md。
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
