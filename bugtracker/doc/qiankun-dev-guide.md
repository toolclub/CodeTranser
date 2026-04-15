# TranVelaPortal 乾坤(qiankun)微前端框架开发指南

> **文档信息**
> - 版本：1.0
> - 创建日期：2026-04-15
> - 适用项目：TranVelaPortal
> - 框架版本：qiankun 2.10+

---

## 目录

1. [项目概述](#1-项目概述)
2. [目录结构](#2-目录结构)
3. [乾坤(qiankun)框架基础](#3-乾坤qiankun框架基础)
4. [主应用(基座)详解](#4-主应用基座详解)
5. [子应用详解](#5-子应用详解)
6. [在主应用开发新页面](#6-在主应用开发新页面)
7. [新增子应用完整流程](#7-新增子应用完整流程)
8. [常见配置说明](#8-常见配置说明)
9. [开发注意事项](#9-开发注意事项)

---

## 1. 项目概述

本项目采用 **阿里乾坤(qiankun)** 微前端框架，主应用(基座)管理多个子应用，实现应用间的独立开发、部署和运行。

### 1.1 项目组成

```
TranVelaPortalApp/
├── TranVelaPortalFrameworkApp/     # 主应用(基座) - vela-base
├── TranVelaPortalTestApp/          # 子应用 - 测试模块
├── TranVelaPortalDevOpsApp/        # 子应用 - DevOps模块
├── TranVelaPortalDeployApp/        # 子应用 - 发布模块
├── TranVelaPortalProjectMgmtApp/   # 子应用 - 项目管理模块
├── TranVelaPortalWorkstationApp/   # 子应用 - 设计模块
└── TranVelaPortalProjectSettingApp/ # 子应用 - 项目设置模块
```

### 1.2 技术栈

| 技术 | 版本要求 |
|------|----------|
| 前端框架 | Vue 3.5+ |
| 路由 | Vue Router 4.5+ |
| 状态管理 | Pinia 3.0+ |
| UI组件库 | Element Plus, DevUI, HUI |
| 微前端框架 | qiankun 2.10+ |
| 构建工具 | Vue CLI 5.0+ |

---

## 2. 目录结构

### 2.1 主应用(基座)目录结构

```
TranVelaPortalFrameworkApp/
└── vela-base/
    ├── src/
    │   ├── api/                    # API接口层
    │   │   ├── auth/               # 认证相关API
    │   │   ├── preference/         # 用户偏好设置API
    │   │   ├── task/               # 任务相关API
    │   │   ├── velaUser/           # Vela用户API
    │   │   ├── workspace/          # 工作空间API
    │   │   └── com.js              # 通用API方法
    │   │
    │   ├── component/              # 公共组件
    │   │   ├── axios-req-tips/     # 请求提示组件
    │   │   ├── coming/             # "即将上线"占位组件
    │   │   ├── fallback/           # 错误边界组件
    │   │   ├── news-notify/        # 消息通知组件
    │   │   ├── page-left/          # 左侧菜单组件
    │   │   └── page-top/           # 顶部导航组件
    │   │
    │   ├── core/                   # 核心工具
    │   │   ├── axios.promise.js    # axios封装
    │   │   ├── cookies.options.js # Cookie配置
    │   │   ├── exception.js        # 异常处理
    │   │   ├── global.axios.interceptors.js  # axios拦截器
    │   │   ├── sse.js              # SSE长连接
    │   │   ├── smart.assistant.manager.js    # 智能助手管理器
    │   │   └── utlis.js            # 工具函数
    │   │
    │   ├── pinia/                  # Pinia状态管理
    │   │   ├── modules/
    │   │   │   ├── auth.js         # 认证状态
    │   │   │   ├── axios.req.tips.js  # 请求提示状态
    │   │   │   ├── devmate.js      # DevMate状态
    │   │   │   ├── vela.auth.js    # Vela认证状态
    │   │   │   └── workspace.js    # 工作空间状态
    │   │   └── index.js            # Pinia入口
    │   │
    │   ├── router/                 # 路由配置
    │   │   ├── index.js            # 路由定义
    │   │   └── router.gate.js      # 路由守卫
    │   │
    │   ├── style/                  # 全局样式
    │   │   └── app.global.css
    │   │
    │   ├── views/                  # 页面视图
    │   │   ├── self/               # 主应用自有页面
    │   │   │   ├── devmate/        # DevMate全屏
    │   │   │   └── workspace/      # 工作空间设置
    │   │   ├── vela-test.vue       # 测试模块入口
    │   │   ├── vela-deploy.vue     # 发布模块入口
    │   │   ├── vela-development.vue # 开发模块入口
    │   │   ├── vela-project-mgmt.vue # 项目管理入口
    │   │   ├── vela-design.vue     # 设计模块入口
    │   │   └── vue-home.vue        # 首页
    │   │
    │   ├── assets/                 # 静态资源
    │   │   └── titile/             # 模块图标
    │   │
    │   ├── App.vue                 # 根组件
    │   ├── main.js                 # 入口文件
    │   └── uem.js                  # UEM配置
    │
    ├── config/                     # 配置文件
    ├── public/                     # 公共资源
    ├── vue.config.js               # Vue CLI配置
    ├── package.json                # 依赖配置
    └── .env.*                      # 环境变量文件
```

### 2.2 子应用目录结构

```
TranVelaPortalTestApp/
└── vela-test/
    ├── src/
    │   ├── api/                    # API接口层
    │   │   ├── autoEnv/            # 自动化环境API
    │   │   ├── cabinet/            # 机柜API
    │   │   ├── environment/        # 测试环境API
    │   │   ├── instrument/         # 仪器API
    │   │   ├── workspace/          # 工作空间API
    │   │   ├── constant.js         # 常量定义
    │   │   └── com.js              # 通用API方法
    │   │
    │   ├── components/             # 公共组件
    │   │   ├── CodeMirrorEditor.vue
    │   │   ├── TelnetTerminal.vue
    │   │   ├── envInfo/            # 环境信息组件
    │   │   └── terminal/           # 终端组件
    │   │
    │   ├── composables/            # 组合式API
    │   │   ├── pagination.js       # 分页逻辑
    │   │   ├── storage.js          # 存储逻辑
    │   │   ├── table.js            # 表格逻辑
    │   │   ├── terminal.js         # 终端逻辑
    │   │   ├── useNetConnection.js # 网络连接
    │   │   ├── userEnvHandle.js    # 用户环境处理
    │   │   └── utils.js            # 工具函数
    │   │
    │   ├── core/                   # 核心工具
    │   │   ├── axios.promise.js
    │   │   ├── com.js
    │   │   ├── exception.js
    │   │   ├── global.axios.interceptors.js
    │   │   └── utlis.js
    │   │
    │   ├── pinia/                  # Pinia状态管理
    │   │   ├── modules/
    │   │   │   ├── auth.js
    │   │   │   ├── cross.page.state.js
    │   │   │   ├── member.mgmt.js
    │   │   │   ├── tenant.js
    │   │   │   └── vela.auth.js
    │   │   └── index.js
    │   │
    │   ├── router/                 # 路由配置
    │   │   ├── index.js            # 路由入口
    │   │   └── sub/                # 子路由模块
    │   │       ├── automationMgmt.router.js
    │   │       ├── environmentDashboard.router.js
    │   │       ├── environmentMgmt.router.js
    │   │       └── environmenrDetail.router.js
    │   │
    │   ├── style/                  # 全局样式
    │   │   └── app.global.css
    │   │
    │   ├── views/                  # 页面视图
    │   │   ├── management/         # 管理页面
    │   │   ├── router/             # 路由页面
    │   │   ├── testEnvironment/    # 测试环境
    │   │   └── automationMgmt/     # 自动化管理
    │   │
    │   ├── assets/                 # 静态资源
    │   │   └── icon/               # 图标
    │   │
    │   ├── App.vue                 # 根组件
    │   ├── main.js                 # 入口文件
    │   └── public-path.js          # qiankun公共路径
    │
    ├── vue.config.js               # Vue CLI配置
    └── package.json                # 依赖配置
```

---

## 3. 乾坤(qiankun)框架基础

### 3.1 qiankun核心概念

| 概念 | 说明 |
|------|------|
| **主应用(基座)** | 负责整体布局、路由管理、子应用注册与加载 |
| **子应用(微应用)** | 独立开发部署的模块，通过UMD方式导出生命周期函数 |
| **沙箱隔离** | qiankun提供JS和CSS隔离，确保子应用间互不影响 |
| **通信机制** | 主应用与子应用通过initGlobalState进行状态共享 |

### 3.2 子应用必须导出的生命周期函数

子应用必须导出以下三个生命周期函数：

```javascript
// 子应用必须导出这三个函数
export async function bootstrap() {
    // 初始化阶段，只调用一次
    console.log('bootstrap');
}

export async function mount(props) {
    // 挂载阶段，每次进入子应用都会调用
    // props 包含主应用传入的数据
    console.log('mount', props);
}

export async function unmount() {
    // 卸载阶段，每次离开子应用都会调用
    console.log('unmount');
}
```

---

## 4. 主应用(基座)详解

### 4.1 主应用入口

**文件位置**: `TranVelaPortalFrameworkApp/vela-base/src/main.js`

**核心流程**:
1. 创建Vue应用
2. 注册Pinia/路由/UI组件
3. 配置qiankun全局状态
4. 启动qiankun

```javascript
// 阶段1: 创建Vue应用
const app = createApp(App)
app.use(pinia)
app.use(DevUI)
app.use(ElementPlus)
app.use(router)

// 阶段2: 配置qiankun全局状态
const actions = initGlobalState(state)
actions.onGlobalStateChange((state) => {
    // 监听状态变化
})

// 阶段3: 注册子应用
const apps = [
    {
        name: 'vela-project-mgmt',
        entry: '/portal/project/mgmt/',
        container: '#vela-project-mgmt',
        activeRule: "/vela-project-mgmt/",
    },
    // ... 其他子应用
]
registerMicroApps(apps)

// 阶段4: 启动qiankun
start()
```

### 4.2 子应用注册配置

在主应用 `main.js` 中的 `apps` 数组定义子应用：

```javascript
const apps = [
    {
        name: '子应用名称',           // 唯一标识
        entry: '子应用入口地址',      // 开发时用本地，生产用CDN
        container: '#容器ID',        // 子应用挂载的DOM元素
        activeRule: '/路由路径/',    // 激活规则(路由匹配)
        props: {                     // 传给子应用的数据
            propsData: 'message'
        }
    }
]
```

### 4.3 主应用路由配置

**文件位置**: `TranVelaPortalFrameworkApp/vela-base/src/router/index.js`

```javascript
export const allRoutes = [
    {
        path: '/',
        name: '首页',
        redirect: '/vela-project-mgmt/',  // 重定向到子应用
        component: () => import('@/views/vue-home.vue'),
    },
    {
        path: '/vela-project-mgmt/',
        name: '项目管理',
        meta: {
            keepAlive: false,
            microApp: true,         // 标识这是微应用
            title: "项目管理",
            icon: proj_mgmt_logo
        },
        component: () => import('@/views/vela-project-mgmt.vue'),
        children: [
            {
                path: '#/overview/',
                name: '概览',
                component: () => import('@/views/vela-project-mgmt.vue'),
            }
        ]
    }
]
```

### 4.4 环境变量配置

**环境变量文件**:
- `.env.dev` - 开发环境
- `.env.development` - 本地开发
- `.env.beta` - 测试环境
- `.env.prod` - 生产环境

**常用环境变量**:

```bash
VUE_APP_VELA_PROJECT_MGMT_REGISTER_URL=/vela-project-mgmt/
VUE_APP_VELA_DEVELOPMENT_MGMT_REGISTER_URL=/vela-development/
VUE_APP_VELA_DEPLOY_REGISTER_URL=/vela-deploy/
VUE_APP_VELA_TEST_REGISTER_URL=/vela-test/
VUE_APP_REGISTER_ALL_APPS=true  # 是否注册所有子应用
```

---

## 5. 子应用详解

### 5.1 子应用入口

**文件位置**: `TranVelaPortalTestApp/vela-test/src/main.js`

**关键点**:
1. **必须引入 public-path.js** - 设置qiankun运行时publicPath
2. **使用 createWebHashHistory** - 子应用必须用Hash模式
3. **条件渲染** - 非qiankun环境时直接挂载

```javascript
import './public-path';  // 必须放在最前面
import {createApp} from 'vue';
import {createRouter, createWebHashHistory} from 'vue-router';

let instance = null;

function render(props = {}) {
    const {container} = props;
    // 挂载到容器或 #app
    instance.mount(container ? container.querySelector('#app') : '#app');
}

// 非qiankun环境(独立运行)直接渲染
if (!window.__POWERED_BY_QIANKUN__) {
    loadApp()
    render();
}

// qiankun生命周期 - 挂载
export async function mount(props) {
    loadApp()
    render(props)
    receive(props)  // 接收主应用数据
}

// qiankun生命周期 - 卸载
export async function unmount() {
    instance.unmount()
}
```

### 5.2 public-path.js

**文件位置**: `vela-test/src/public-path.js`

```javascript
if (window.__POWERED_BY_QIANKUN__) {
    // eslint-disable-next-line no-undef
    __webpack_public_path__ = window.__INJECTED_PUBLIC_PATH_BY_QIANKUN__;
}
```

### 5.3 子应用路由配置

子应用路由使用 **Hash模式**：

```javascript
// vela-test/src/router/index.js
import testEnvironmentsRoutes from "@/router/sub/environmentDashboard.router";

const routes = [];

testEnvironmentsRoutes.map((item) => {
    routes.push(item)
})

export default routes;
```

### 5.4 接收主应用数据

```javascript
function receive(props) {
    // 监听主应用状态变化
    props.onGlobalStateChange(
        (value, prev) => {
            console.log('新数据:', value);
            console.log('老数据:', prev);
            
            // 更新本地store
            const tenantObj = value.propsMsg.workspace;
            tenantStore.updateTenant(tenantObj);
            
            const userObj = value.propsMsg.auth;
            memberMgmtStore.updateUserInfo(userObj);
        },
        true  // 立即执行一次
    );
}
```

---

## 6. 在主应用开发新页面

假设需求：在主应用中新增一个"统计报表"页面

### Step 1: 创建页面组件

在 `vela-base/src/views/` 目录下创建新页面：

```vue
<!-- src/views/statistics/report.vue -->
<template>
  <div class="report-container">
    <h1>统计报表</h1>
    <el-card>
      <div class="chart-wrapper">
        <!-- 图表内容 -->
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

const dataList = ref([])

onMounted(() => {
  // 初始化数据
})
</script>

<style scoped>
.report-container {
  padding: 20px;
}
.chart-wrapper {
  height: 400px;
}
</style>
```

### Step 2: 配置路由

编辑 `vela-base/src/router/index.js`：

```javascript
// 1. 先import组件
import report from "../assets/titile/report_logo.png"

// 2. 在 allRoutes 数组中添加路由
{
    path: '/statistics/report',
    name: '统计报表',
    meta: {
        keepAlive: false,
        microApp: false,  // 主应用自有页面设为false
        title: "统计报表",
        icon: report
    },
    component: () => import('@/views/statistics/report.vue'),
}
```

### Step 3: 配置菜单(可选)

如果需要在左侧菜单显示，修改 `vela-base/src/component/page-left/base-page-left_menu.vue`：

```vue
<!-- 添加菜单项 -->
<el-menu-item index="/statistics/report">
    <img :src="reportIcon" class="menu-icon" />
    <span>统计报表</span>
</el-menu-item>
```

### Step 4: 启动验证

```bash
cd TranVelaPortalFrameworkApp/vela-base
npm run serve
```

访问 `http://dev.huawei.com:5174/statistics/report` 验证页面。

---

## 7. 新增子应用完整流程

假设需求：新增一个"数据分析"子应用 `vela-analytics`

### Step 1: 创建子应用目录结构

```
TranVelaPortalAnalyticsApp/
└── vela-analytics/
    ├── src/
    │   ├── api/
    │   ├── components/
    │   ├── composables/
    │   ├── core/
    │   ├── pinia/
    │   │   └── modules/
    │   ├── router/
    │   │   └── sub/
    │   ├── style/
    │   ├── views/
    │   ├── assets/
    │   ├── App.vue
    │   ├── main.js
    │   └── public-path.js
    ├── vue.config.js
    └── package.json
```

### Step 2: 配置 package.json

```json
{
  "name": "vela-analytics",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "serve": "vue-cli-service serve",
    "build": "vue-cli-service build"
  },
  "dependencies": {
    "vue": "^3.5.0",
    "vue-router": "^4.5.0",
    "pinia": "^3.0.0",
    "element-plus": "^2.10.0",
    "qiankun": "^2.10.0"
  }
}
```

### Step 3: 配置 vue.config.js

```javascript
const { name } = require('./package');

module.exports = {
  publicPath: process.env.VUE_APP_BASE_CONTEXT,  // 如: '/portal/analytics/'
  outputDir: "dist/" + process.env.VUE_APP_BASE_CONTEXT,
  devServer: {
    port: 3006,
    headers: {
      'Access-Control-Allow-Origin': '*',
    },
    proxy: {
      '/mirco_service_gw/': {
        target: `https://tran.dp-beta.huawei.com/`,
        ws: true,
        changeOrigin: true,
        pathRewrite: {
          '^/mirco_service_gw/': ''
        }
      },
    }
  },
  configureWebpack: {
    output: {
      library: `${name}`,
      libraryTarget: 'umd',
      chunkLoadingGlobal: `webpackJsonp_${name}`,
    },
  },
}
```

### Step 4: 配置 main.js

```javascript
import './public-path';
import { createApp } from 'vue';
import { createRouter, createWebHashHistory } from 'vue-router';
import ElementPlus from 'element-plus';
import 'element-plus/theme-chalk/index.css';
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import App from './App.vue';
import routes from './router';
import pinia from "@/pinia";

let instance = null;
let router = null;
let history = null;

function render(props = {}) {
  const { container } = props;
  instance.mount(container ? container.querySelector('#app') : '#app');
}

function loadApp() {
  instance = createApp(App);
  
  // 根据环境选择基础路径
  history = createWebHashHistory(
    window.__POWERED_BY_QIANKUN__ 
      ? process.env.VUE_APP_PROJECT_QIANKUN_CONTEXT 
      : process.env.VUE_APP_BASE_CONTEXT
  );
  
  router = createRouter({
    history,
    routes,
  });
  
  instance.use(pinia);
  instance.use(ElementPlus, { locale: zhCn });
  instance.use(router);
}

// 独立运行
if (!window.__POWERED_BY_QIANKUN__) {
  loadApp();
  render();
}

// qiankun生命周期
export async function bootstrap() {
  console.log('bootstrap');
}

export async function mount(props) {
  loadApp();
  render(props);
  receive(props);
}

export async function unmount() {
  instance.unmount();
  instance = null;
  router = null;
  history.destroy();
}

// 接收主应用数据
function receive(props) {
  props.onGlobalStateChange((value, prev) => {
    console.log('主应用数据变化:', value);
  }, true);
}
```

### Step 5: 配置 public-path.js

```javascript
if (window.__POWERED_BY_QIANKUN__) {
  // eslint-disable-next-line no-undef
  __webpack_public_path__ = window.__INJECTED_PUBLIC_PATH_BY_QIANKUN__;
}
```

### Step 6: 主应用注册子应用

编辑 `vela-base/src/main.js`：

```javascript
// 在 apps 数组中添加
{
    name: 'vela-analytics',
    entry: '/portal/analytics/',
    container: '#vela-analytics',
    activeRule: process.env.VUE_APP_VELA_ANALYTICS_REGISTER_URL,
    props: {
        propsData: 'message: vela-analytics'
    }
}
```

### Step 7: 配置主应用路由

编辑 `vela-base/src/router/index.js`：

```javascript
import analytics_logo from "../assets/titile/analytics_logo.png"

// 添加路由
{
    path: process.env.VUE_APP_VELA_ANALYTICS_REGISTER_URL,
    name: '数据分析',
    meta: {
        keepAlive: false,
        microApp: true,
        title: "数据分析",
        icon: analytics_logo
    },
    component: () => import('@/views/vela-analytics.vue'),
    children: [
        {
            path: '#/overview/',
            name: '数据概览',
            component: () => import('@/views/vela-analytics.vue'),
        }
    ]
}
```

### Step 8: 配置环境变量

在 `.env.dev` 和 `.env.beta` 等文件中添加：

```bash
VUE_APP_VELA_ANALYTICS_REGISTER_URL=/vela-analytics/
VUE_APP_VELA_ANALYTICS_BASE_CONTEXT=/portal/analytics/
VUE_APP_VELA_ANALYTICS_PROJECT_QIANKUN_CONTEXT=/portal/analytics/
```

### Step 9: 配置主应用 vue.config.js 代理

```javascript
proxy: {
    '/portal/analytics/': {
        target: `http://localhost:3006/portal/analytics/`,
        ws: true,
        changeOrigin: true,
        pathRewrite: {
            '^/portal/analytics/': ''
        }
    }
}
```

### Step 10: 启动验证

```bash
# 启动子应用
cd TranVelaPortalAnalyticsApp/vela-analytics
npm run serve

# 启动主应用
cd TranVelaPortalFrameworkApp/vela-base
npm run serve
```

访问 `http://dev.huawei.com:5174/vela-analytics/` 验证。

---

## 8. 常见配置说明

### 8.1 主应用 vue.config.js 代理配置

```javascript
proxy: {
    '/mirco_service_gw/': {
        target: 'https://tran.dp-dev.huawei.com/',
        ws: true,
        changeOrigin: true,
        pathRewrite: { '^/mirco_service_gw/': '' }
    },
    '/portal/test/': {
        target: 'https://tran.dp-dev.huawei.com/portal/test/',
        ws: true,
        changeOrigin: true,
        pathRewrite: { '^/portal/test/': '' }
    }
}
```

### 8.2 子应用间通信

**主应用设置全局状态**:

```javascript
// 主应用
const state = reactive({
    user: { name: '张三' },
    workspace: { id: '123' }
});
const actions = initGlobalState(state);
actions.setGlobalState(state);
```

**子应用监听状态变化**:

```javascript
// 子应用
props.onGlobalStateChange((value, prev) => {
    console.log('状态变化:', value);
}, true);
```

### 8.3 CSS隔离

qiankun自动处理CSS隔离，如需手动控制可在vue.config.js中配置：

```javascript
configureWebpack: {
    module: {
        rules: [
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader']
            }
        ]
    }
}
```

---

## 9. 开发注意事项

### 9.1 常见问题

| 问题 | 解决方案 |
|------|----------|
| 子应用样式丢失 | 检查public-path.js是否正确引入 |
| 子应用无法加载 | 检查activeRule路径是否匹配 |
| 主应用状态不同步 | 确保onGlobalStateChange正确调用 |
| 静态资源404 | 检查publicPath配置和资源路径 |
| 跨域问题 | 配置devServer headers允许跨域 |

### 9.2 开发技巧

1. **独立运行子应用**: 开发时可让子应用独立运行调试
2. **热更新**: 主应用修改后刷新子应用也可用
3. **调试**: 浏览器控制台查看 `__POWERED_BY_QIANKUN__` 判断环境
4. **状态管理**: 复杂数据使用Pinia，简单数据用qiankun通信

### 9.3 构建部署

```bash
# 子应用构建
cd vela-test
npm run build  # 输出到 dist/portal/test/

# 主应用构建
cd vela-base
npm run build:prod
```

---

## 附录: 关键文件速查

| 功能 | 文件路径 |
|------|----------|
| 主应用入口 | `vela-base/src/main.js` |
| 主应用路由 | `vela-base/src/router/index.js` |
| 主应用组件 | `vela-base/src/App.vue` |
| 子应用入口 | `vela-test/src/main.js` |
| 子应用路由 | `vela-test/src/router/index.js` |
| 子应用组件 | `vela-test/src/App.vue` |
| 主应用配置 | `vela-base/vue.config.js` |
| 子应用配置 | `vela-test/vue.config.js` |
| 主应用路由守卫 | `vela-base/src/router/router.gate.js` |
| 公共工具函数 | `vela-base/src/core/utlis.js` |
