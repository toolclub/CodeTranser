/**
 * BugTracker 路由配置
 *
 * 使用方式：在 src/router/index.js 中引入并注册
 *
 * import bugTrackerRoutes from '@/router/sub/bugTracker.router'
 * bugTrackerRoutes.map(item => routes.push(item))
 */
const bugTrackerRoutes = [
    {
        path: '/bugtracker/',
        name: 'BugTrackerList',
        component: () => import('@/views/bugTracker/BugTrackerList.vue'),
        meta: { title: 'BugTracker' },
    },
    {
        path: '/bugtracker/create',
        name: 'BugTrackerCreate',
        component: () => import('@/views/bugTracker/BugTrackerCreate.vue'),
        meta: { title: '新增分析' },
    },
]

export default bugTrackerRoutes
