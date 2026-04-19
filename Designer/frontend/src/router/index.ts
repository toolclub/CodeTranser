import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: () => import('@/pages/Home.vue') },
  { path: '/graphs', name: 'graph-list', component: () => import('@/pages/GraphList.vue') },
  {
    path: '/canvas/:graphId?',
    name: 'canvas-editor',
    component: () => import('@/pages/CanvasEditor.vue'),
  },
  {
    path: '/templates',
    name: 'template-library',
    component: () => import('@/pages/TemplateLibrary.vue'),
  },
  {
    path: '/template-editor/:id?',
    name: 'template-editor',
    component: () => import('@/pages/TemplateEditor.vue'),
  },
  {
    path: '/scenarios/:graphVersionId?',
    name: 'scenarios',
    component: () => import('@/pages/Scenarios.vue'),
  },
  { path: '/runs', name: 'run-list', component: () => import('@/pages/RunList.vue') },
  { path: '/runs/:id', name: 'run-detail', component: () => import('@/pages/RunDetail.vue') },
  {
    path: '/code-diff/:runId?',
    name: 'code-diff',
    component: () => import('@/pages/CodeDiff.vue'),
  },
  { path: '/review/:id?', name: 'review', component: () => import('@/pages/Review.vue') },
  {
    path: '/no-permission',
    name: 'no-permission',
    component: () => import('@/pages/NoPermission.vue'),
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
