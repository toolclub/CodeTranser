<template>
    <div class="bug-tracker-create">
        <!-- 顶部导航栏 -->
        <div class="top-bar">
            <button class="back-btn" @click="handleBack">
                <el-icon><ArrowLeft /></el-icon>
                {{ currentStep === 1 ? '返回列表' : '返回上一步' }}
            </button>
            <h1 class="page-title">新增分析</h1>
        </div>

        <!-- 步骤导航 -->
        <div class="step-navigation">
            <template v-for="(step, idx) in STEPS" :key="step.key">
                <div :class="['step-item', stepState(idx + 1)]">
                    <div class="step-circle">
                        <el-icon v-if="stepState(idx + 1) === 'completed'"><Check /></el-icon>
                        <span v-else>{{ idx + 1 }}</span>
                    </div>
                    <span class="step-label">{{ step.label }}</span>
                </div>
                <div v-if="idx < STEPS.length - 1" :class="['step-connector', stepState(idx + 1) === 'completed' ? 'completed' : '']" />
            </template>
        </div>

        <!-- 主内容区 -->
        <div class="main-content">
            <div class="section-card">
                <!-- ══════════════════ STEP 1：基础配置 ══════════════════ -->
                <template v-if="currentStep === 1">
                    <div class="section-header">
                        <h2 class="section-title">
                            <el-icon><Setting /></el-icon>
                            基础配置
                        </h2>
                    </div>
                    <div class="section-body">
                        <!-- 验证模式 -->
                        <div class="form-group">
                            <label class="form-label">验证模式</label>
                            <div class="mode-tabs">
                                <div
                                    :class="['mode-tab', form.mode === 'single' ? 'active' : '']"
                                    @click="form.mode = 'single'"
                                >
                                    <el-icon><Monitor /></el-icon>
                                    单节点验证
                                </div>
                                <div
                                    :class="['mode-tab', form.mode === 'multi' ? 'active' : '']"
                                    @click="form.mode = 'multi'"
                                >
                                    <el-icon><Share /></el-icon>
                                    多节点验证
                                </div>
                            </div>
                        </div>

                        <!-- 单节点配置 -->
                        <template v-if="form.mode === 'single'">
                            <div class="form-group">
                                <label class="form-label">代码仓库</label>
                                <el-input v-model="form.repo" placeholder="请输入内容" class="form-input" />
                            </div>
                            <div class="form-group">
                                <label class="form-label">目标分支</label>
                                <el-input v-model="form.branch" placeholder="请输入内容" class="form-input" />
                            </div>
                            <div class="form-group">
                                <label class="form-label">
                                    Commit ID
                                    <span class="optional">（可选，不填则使用最新 commit）</span>
                                </label>
                                <el-input v-model="form.commitId" placeholder="请输入内容" class="form-input" />
                            </div>
                        </template>

                        <!-- 多节点配置 -->
                        <template v-if="form.mode === 'multi'">
                            <div class="form-group">
                                <label class="form-label">代码仓库</label>
                                <el-input v-model="form.repo" placeholder="请输入内容" class="form-input" />
                            </div>
                            <div class="form-group">
                                <label class="form-label">目标分支</label>
                                <el-input v-model="form.branch" placeholder="请输入内容" class="form-input" />
                            </div>
                            <div class="form-group">
                                <label class="form-label">起始 Commit ID</label>
                                <el-input v-model="form.startCommitId" placeholder="请输入内容" class="form-input" />
                            </div>
                            <div class="form-group">
                                <label class="form-label">结束 Commit ID</label>
                                <el-input v-model="form.endCommitId" placeholder="请输入内容" class="form-input" />
                            </div>
                        </template>
                    </div>
                    <div class="footer-actions">
                        <button class="btn btn-prev" @click="goToList">
                            <el-icon><ArrowLeft /></el-icon>
                            上一步
                        </button>
                        <button class="btn btn-next" @click="goStep2">
                            下一步
                            <el-icon><ArrowRight /></el-icon>
                        </button>
                    </div>
                </template>

                <!-- ══════════════════ STEP 2：用例配置 ══════════════════ -->
                <template v-if="currentStep === 2">
                    <div class="section-header">
                        <h2 class="section-title">
                            <el-icon><List /></el-icon>
                            用例配置
                        </h2>
                    </div>
                    <div class="section-body">
                        <!-- 工具栏 -->
                        <div class="toolbar">
                            <el-input
                                v-model="caseSearch"
                                placeholder="请输入用例编号搜索内容……"
                                clearable
                                style="flex: 1; min-width: 250px"
                                @input="handleCaseSearch"
                            >
                                <template #prefix><el-icon><Search /></el-icon></template>
                            </el-input>
                            <el-button @click="resetCaseSelection">
                                <el-icon><RefreshLeft /></el-icon>
                                重置勾选
                            </el-button>
                            <div class="case-count">
                                <el-icon><Select /></el-icon>
                                当前选中：<strong>{{ checkedCaseCount }}</strong> 个用例
                            </div>
                        </div>

                        <!-- 用例树 -->
                        <div v-loading="caseTreeLoading" class="case-tree-wrap">
                            <el-tree
                                ref="treeRef"
                                :data="caseTreeData"
                                :props="treeProps"
                                :filter-node-method="filterNode"
                                node-key="id"
                                show-checkbox
                                default-expand-all
                                @check="updateCheckedCount"
                            >
                                <template #default="{ data }">
                                    <span class="tree-node-label">
                                        <el-icon v-if="data.children?.length" class="node-icon folder">
                                            <Folder />
                                        </el-icon>
                                        <el-icon v-else class="node-icon file">
                                            <Document />
                                        </el-icon>
                                        {{ data.label }}
                                    </span>
                                </template>
                            </el-tree>
                        </div>
                    </div>
                    <div class="footer-actions">
                        <button class="btn btn-prev" @click="currentStep = 1">
                            <el-icon><ArrowLeft /></el-icon>
                            上一步
                        </button>
                        <button class="btn btn-next" @click="goStep3">
                            下一步
                            <el-icon><ArrowRight /></el-icon>
                        </button>
                    </div>
                </template>

                <!-- ══════════════════ STEP 3：环境配置 ══════════════════ -->
                <template v-if="currentStep === 3">
                    <div class="section-header">
                        <h2 class="section-title">
                            <el-icon><Monitor /></el-icon>
                            环境配置
                        </h2>
                    </div>
                    <div class="section-body">
                        <div class="info-tip">
                            <el-icon class="tip-icon"><InfoFilled /></el-icon>
                            <p>按物理拓扑分组配置环境，默认选择上次用例使用环境</p>
                        </div>

                        <div v-loading="envLoading" class="env-cards">
                            <div v-for="env in form.environments" :key="env.id" class="env-card">
                                <div class="env-icon">
                                    <el-icon><Cpu /></el-icon>
                                </div>
                                <div class="env-info">
                                    <div class="env-title">{{ env.name }}</div>
                                    <div class="env-label">{{ env.label }}</div>
                                </div>
                                <div class="env-input-group">
                                    <span class="env-input-label">环境序号</span>
                                    <el-input
                                        v-model="env.envIndex"
                                        style="width: 100px"
                                        class="env-index-input"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="footer-actions">
                        <button class="btn btn-prev" @click="currentStep = 2">
                            <el-icon><ArrowLeft /></el-icon>
                            上一步
                        </button>
                        <button class="btn btn-next" @click="currentStep = 4">
                            下一步
                            <el-icon><ArrowRight /></el-icon>
                        </button>
                    </div>
                </template>

                <!-- ══════════════════ STEP 4：执行操作 ══════════════════ -->
                <template v-if="currentStep === 4">
                    <div class="section-header">
                        <h2 class="section-title">
                            <el-icon><VideoPlay /></el-icon>
                            执行操作
                        </h2>
                    </div>
                    <div class="section-body">
                        <!-- 配置汇总 -->
                        <div class="summary-section">
                            <div class="summary-title">
                                <el-icon><Tickets /></el-icon>
                                配置汇总
                            </div>
                            <table class="summary-table">
                                <tr>
                                    <th>仓库</th>
                                    <td>{{ form.repo || '-' }}</td>
                                </tr>
                                <tr>
                                    <th>分支</th>
                                    <td>{{ form.branch || '-' }}</td>
                                </tr>
                                <tr>
                                    <th>验证模式</th>
                                    <td>{{ form.mode === 'single' ? '单节点验证' : '多节点验证' }}</td>
                                </tr>
                                <tr>
                                    <th>commit 节点</th>
                                    <td>
                                        <template v-if="form.mode === 'single'">
                                            {{ form.commitId || '（使用最新 commit）' }}
                                        </template>
                                        <template v-else>
                                            {{ form.startCommitId }} ~ {{ form.endCommitId }}
                                        </template>
                                    </td>
                                </tr>
                                <tr>
                                    <th>已勾选用例</th>
                                    <td>
                                        <ul v-if="form.selectedCases.length" class="summary-cases">
                                            <li v-for="c in form.selectedCases" :key="c.id">
                                                {{ c.label }}
                                                <span v-if="form.environments.length">
                                                    （环境: {{ form.environments[0]?.name }} {{ form.environments[0]?.envIndex }}）
                                                </span>
                                            </li>
                                        </ul>
                                        <span v-else class="no-cases">未选择用例</span>
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <!-- 日志输出（执行后显示） -->
                        <div v-if="executing || executeDone" class="log-section">
                            <div class="log-title">
                                <el-icon><DataLine /></el-icon>
                                日志输出
                                <el-tag v-if="executing" type="primary" size="small" style="margin-left: 8px">执行中…</el-tag>
                            </div>
                            <div ref="logBoxRef" class="log-output">
                                <p
                                    v-for="(line, i) in logLines"
                                    :key="i"
                                    :class="['log-line', logLineClass(line)]"
                                >{{ line }}</p>
                            </div>
                        </div>

                        <!-- 结果汇总（执行完成后显示） -->
                        <div v-if="executeDone" class="result-section">
                            <div class="result-title">
                                <el-icon><PieChart /></el-icon>
                                结果汇总
                            </div>
                            <div class="result-cards">
                                <div class="result-card success">
                                    <div class="result-icon success">
                                        <el-icon><Check /></el-icon>
                                    </div>
                                    <div class="result-number success">{{ result.success }}</div>
                                    <div class="result-label">成功用例</div>
                                </div>
                                <div class="result-card failed">
                                    <div class="result-icon failed">
                                        <el-icon><Close /></el-icon>
                                    </div>
                                    <div class="result-number failed">{{ result.failed }}</div>
                                    <div class="result-label">失败用例</div>
                                </div>
                                <div class="result-card total">
                                    <div class="result-icon total">
                                        <el-icon><List /></el-icon>
                                    </div>
                                    <div class="result-number total">{{ result.total }}</div>
                                    <div class="result-label">总用例数</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="footer-actions">
                        <button class="btn btn-prev" :disabled="executing" @click="currentStep = 3">
                            <el-icon><ArrowLeft /></el-icon>
                            上一步
                        </button>
                        <div class="btn-group">
                            <button v-if="!executeDone" class="btn btn-cancel" :disabled="executing" @click="goToList">
                                <el-icon><CircleClose /></el-icon>
                                取消
                            </button>
                            <button v-if="!executeDone && !executing" class="btn btn-primary" @click="startExecution">
                                <el-icon><Aim /></el-icon>
                                开始定位
                            </button>
                            <button v-if="executing" class="btn btn-primary" disabled>
                                <el-icon class="rotating"><Loading /></el-icon>
                                执行中…
                            </button>
                            <button v-if="executeDone" class="btn btn-primary" @click="goToList">
                                <el-icon><Check /></el-icon>
                                完成返回
                            </button>
                        </div>
                    </div>
                </template>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
    ArrowLeft, ArrowRight, Check, Close, Setting, Monitor, Share,
    List, Search, RefreshLeft, Select, Folder, Document,
    InfoFilled, Cpu, VideoPlay, Tickets, DataLine, PieChart,
    CircleClose, Aim, Loading,
} from '@element-plus/icons-vue'
import { getCaseTree, getMatchedEnvironments, createAnalysisTask, getTaskLogs, getTaskResult } from '@/api/bugTracker/index'

const router = useRouter()

// ─── 步骤定义 ─────────────────────────────────────────────────────────────────
const STEPS = [
    { key: 'basic', label: '基础配置' },
    { key: 'case',  label: '用例配置' },
    { key: 'env',   label: '环境配置' },
    { key: 'exec',  label: '执行操作' },
]

const currentStep = ref(1)

function stepState(n) {
    if (n < currentStep.value)  return 'completed'
    if (n === currentStep.value) return 'active'
    return 'inactive'
}

// ─── 表单数据（贯穿全流程） ────────────────────────────────────────────────────
const form = reactive({
    // Step 1
    mode:          'single', // 'single' | 'multi'
    repo:          '',
    branch:        '',
    commitId:      '',
    startCommitId: '',
    endCommitId:   '',
    // Step 2（由树形选中结果填入）
    selectedCases: [],       // [{ id, label }]
    // Step 3（由接口填入后用户调整）
    environments:  [],       // [{ id, name, label, envIndex }]
})

// ─── STEP 2：用例树 ───────────────────────────────────────────────────────────
const treeRef         = ref(null)
const caseSearch      = ref('')
const caseTreeLoading = ref(false)
const caseTreeData    = ref([])
const checkedCaseCount = ref(0)

const treeProps = { children: 'children', label: 'label' }

function filterNode(value, data) {
    if (!value) return true
    return data.label.includes(value)
}

function handleCaseSearch(val) {
    treeRef.value?.filter(val)
}

function updateCheckedCount() {
    const leaves = treeRef.value?.getCheckedNodes(true) ?? []
    checkedCaseCount.value = leaves.length
}

function resetCaseSelection() {
    treeRef.value?.setCheckedKeys([])
    checkedCaseCount.value = 0
}

async function loadCaseTree() {
    caseTreeLoading.value = true
    try {
        /**
         * TODO: 接口就绪后替换以下 mock 数据
         *
         * const res = await getCaseTree({ repo: form.repo, branch: form.branch })
         * caseTreeData.value = res
         */

        // ── Mock 树数据（接口就绪后删除） ────────────────────────────────────
        await new Promise(r => setTimeout(r, 500))
        caseTreeData.value = [
            {
                id: 'root', label: 'Cases', children: [
                    {
                        id: '01_BLACKTEST', label: '01_BLACKTEST', children: [
                            { id: 'TC_LOG_NORMAL_RECORD_FUNC_004',    label: 'TC_LOG_NORMAL_RECORD_FUNC_004' },
                            { id: 'TC_ETH_LANSWITCH_PORT_FUNC_016',   label: 'TC_ETH_LANSWITCH_PORT_FUNC_016' },
                        ],
                    },
                    {
                        id: '00_INIT', label: '00_INIT', children: [
                            { id: 'TC_INIT_SYSTEM_BOOT_001', label: 'TC_INIT_SYSTEM_BOOT_001' },
                        ],
                    },
                    {
                        id: '01_ATM', label: '01_ATM', children: [
                            { id: 'TC_ATM_CONNECTIVITY_TEST_001', label: 'TC_ATM_CONNECTIVITY_TEST_001' },
                        ],
                    },
                    {
                        id: '02_ETH', label: '02_ETH', children: [
                            { id: 'TC_ETH_BANDWIDTH_TEST_001', label: 'TC_ETH_BANDWIDTH_TEST_001' },
                        ],
                    },
                    {
                        id: '04_FIREWALL', label: '04_FIREWALL', children: [
                            { id: 'TC_FIREWALL_RULE_TEST_001', label: 'TC_FIREWALL_RULE_TEST_001' },
                        ],
                    },
                    {
                        id: '01_PACKETFILTER', label: '01_PACKETFILTER', children: [
                            {
                                id: '01_IPV4', label: '01_IPV4', children: [
                                    {
                                        id: 'func_test', label: '功能测试', children: [
                                            {
                                                id: 'ping_group', label: '主机禁PING和网管禁PING地址同时配置测试', children: [
                                                    { id: '3920R1',    label: '3920R1' },
                                                    { id: 'RootBBU',   label: 'RootBBU' },
                                                    { id: 'GTMUcc',    label: 'GTMUcc' },
                                                    { id: 'GTMUCOBTs', label: 'GTMUCOBTs' },
                                                ],
                                            },
                                            { id: 'ping_stats', label: '主机禁PING和网管禁PING地址同时配置统计' },
                                        ],
                                    },
                                    { id: 'perf_test', label: '性能测试' },
                                ],
                            },
                        ],
                    },
                ],
            },
        ]
        // 默认勾选前两个叶子节点（与低保真一致）
        treeRef.value?.setCheckedKeys(['TC_LOG_NORMAL_RECORD_FUNC_004', 'TC_ETH_LANSWITCH_PORT_FUNC_016', '3920R1', 'RootBBU', 'GTMUcc', 'GTMUCOBTs'])
        updateCheckedCount()
        // ────────────────────────────────────────────────────────────────────
    } catch {
        ElMessage.error('获取用例列表失败')
    } finally {
        caseTreeLoading.value = false
    }
}

async function goStep2() {
    if (!form.repo || !form.branch) {
        ElMessage.warning('请填写代码仓库和目标分支')
        return
    }
    if (form.mode === 'multi' && (!form.startCommitId || !form.endCommitId)) {
        ElMessage.warning('请填写起始和结束 Commit ID')
        return
    }
    currentStep.value = 2
    await loadCaseTree()
}

// ─── STEP 3：环境配置 ─────────────────────────────────────────────────────────
const envLoading = ref(false)

async function loadEnvironments() {
    envLoading.value = true
    try {
        const leaves = treeRef.value?.getCheckedNodes(true) ?? []
        form.selectedCases = leaves.map(n => ({ id: n.id, label: n.label }))

        /**
         * TODO: 接口就绪后替换以下 mock 数据
         *
         * const res = await getMatchedEnvironments({ selectedCaseIds: form.selectedCases.map(c => c.id) })
         * form.environments = res
         */

        // ── Mock 环境数据（接口就绪后删除） ──────────────────────────────────
        await new Promise(r => setTimeout(r, 400))
        form.environments = [
            { id: 'env1', name: 'FO1_UMPTB_TOPO1_NEW',            label: 'UMPTB 物理拓扑环境',          envIndex: '107' },
            { id: 'env2', name: 'FO3_UMPTEC05_TOPO1_NEW',          label: 'UMPTEC05 物理拓扑环境',        envIndex: '310' },
            { id: 'env3', name: 'FO5_UMPPTH_UMPTG_TOPO2_LB2',      label: 'UMPPTH+UMPTG 组合拓扑环境',   envIndex: '544' },
        ]
        // ────────────────────────────────────────────────────────────────────
    } catch {
        ElMessage.error('获取环境配置失败')
    } finally {
        envLoading.value = false
    }
}

async function goStep3() {
    const leaves = treeRef.value?.getCheckedNodes(true) ?? []
    if (!leaves.length) {
        ElMessage.warning('请至少选择一个用例')
        return
    }
    currentStep.value = 3
    await loadEnvironments()
}

// ─── STEP 4：执行操作 ─────────────────────────────────────────────────────────
const executing   = ref(false)
const executeDone = ref(false)
const logLines    = ref([])
const logBoxRef   = ref(null)
const result      = reactive({ total: 0, success: 0, failed: 0 })

let pollTimer    = null
let logOffset    = 0
let currentTaskId = ''

function logLineClass(line) {
    if (line.includes('[SUCCESS]')) return 'log-success'
    if (line.includes('[ERROR]'))   return 'log-error'
    if (line.includes('[WARNING]')) return 'log-warning'
    return 'log-info'
}

async function scrollLogToBottom() {
    await nextTick()
    if (logBoxRef.value) {
        logBoxRef.value.scrollTop = logBoxRef.value.scrollHeight
    }
}

async function pollLogs() {
    try {
        /**
         * TODO: 接口就绪后替换以下 mock 轮询逻辑
         *
         * const res = await getTaskLogs(currentTaskId, logOffset)
         * logLines.value.push(...res.lines)
         * logOffset += res.lines.length
         * scrollLogToBottom()
         * if (!res.hasMore) {
         *   stopPolling()
         *   const taskResult = await getTaskResult(currentTaskId)
         *   result.total   = taskResult.total
         *   result.success = taskResult.success
         *   result.failed  = taskResult.failed
         *   executing.value   = false
         *   executeDone.value = true
         * }
         */

        // ── Mock 日志轮询（接口就绪后删除） ──────────────────────────────────
        const mockLogs = [
            '[INFO] 开始执行用例：TC_LOG_NORMAL_RECORD_FUNC_004',
            '[SUCCESS] TC_LOG_NORMAL_RECORD_FUNC_004 - 用例执行通过',
            '[INFO] 开始执行用例：TC_ETH_LANSWITCH_PORT_FUNC_016',
            '[SUCCESS] TC_ETH_LANSWITCH_PORT_FUNC_016 - 用例执行通过',
            '[INFO] 开始执行用例：3920R1',
            '[ERROR] 3920R1 - 用例执行失败：断言失败',
            '[INFO] 开始执行用例：RootBBU',
            '[SUCCESS] RootBBU - 用例执行通过',
            '[INFO] 开始执行用例：GTMUcc',
            '[SUCCESS] GTMUcc - 用例执行通过',
            '[INFO] 所有用例执行完成',
            '[SUCCESS] 测试报告已生成：report-' + new Date().toISOString().slice(0, 10).replace(/-/g, '') + '.html',
        ]
        const now = new Date().toTimeString().slice(0, 8)
        const batch = mockLogs.slice(logOffset, logOffset + 2)
        batch.forEach(l => logLines.value.push(`${l.split('] ')[0]}] ${now} ${l.split('] ').slice(1).join('] ')}`))
        logOffset += batch.length
        scrollLogToBottom()

        if (logOffset >= mockLogs.length) {
            stopPolling()
            result.total   = form.selectedCases.length
            result.success = form.selectedCases.length - 1
            result.failed  = 1
            executing.value   = false
            executeDone.value = true
        }
        // ────────────────────────────────────────────────────────────────────
    } catch {
        stopPolling()
        ElMessage.error('日志拉取失败')
        executing.value = false
    }
}

function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
    }
}

async function startExecution() {
    executing.value   = true
    executeDone.value = false
    logLines.value    = []
    logOffset         = 0

    try {
        /**
         * TODO: 接口就绪后替换以下 mock
         *
         * const res = await createAnalysisTask({
         *   mode:          form.mode,
         *   repo:          form.repo,
         *   branch:        form.branch,
         *   commitId:      form.commitId,
         *   startCommitId: form.startCommitId,
         *   endCommitId:   form.endCommitId,
         *   selectedCaseIds: form.selectedCases.map(c => c.id),
         *   environments:  form.environments.map(e => ({ id: e.id, envIndex: e.envIndex })),
         * })
         * currentTaskId = res.taskId
         */
        currentTaskId = 'mock-task-' + Date.now() // TODO: 替换为真实 taskId
        // ────────────────────────────────────────────────────────────────────

        // 开始轮询日志，每 1.5 秒拉取一次
        pollTimer = setInterval(pollLogs, 1500)
    } catch {
        executing.value = false
        ElMessage.error('任务提交失败，请重试')
    }
}

// ─── 通用导航 ─────────────────────────────────────────────────────────────────
function handleBack() {
    if (currentStep.value === 1) {
        goToList()
    } else {
        currentStep.value--
    }
}

function goToList() {
    stopPolling()
    router.push({ name: 'BugTrackerList' })
}

onUnmounted(stopPolling)
</script>

<style scoped>
/* ─── 整体布局 ─────────────────────────────────────────────────────────────── */
.bug-tracker-create {
    min-height: 100vh;
    background: #f0f2f5;
}

/* ─── 顶部导航栏 ───────────────────────────────────────────────────────────── */
.top-bar {
    display: flex;
    align-items: center;
    padding: 16px 30px;
    background: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    position: sticky;
    top: 0;
    z-index: 100;
}

.back-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 8px;
    cursor: pointer;
    color: #666;
    font-size: 14px;
    margin-right: 30px;
    transition: all 0.2s;
}
.back-btn:hover { background: #eee; color: #333; }

.page-title {
    font-size: 18px;
    font-weight: 600;
    color: #1a237e;
}

/* ─── 步骤导航 ─────────────────────────────────────────────────────────────── */
.step-navigation {
    background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
    padding: 36px 60px;
    display: flex;
    justify-content: center;
    align-items: center;
}

.step-item {
    display: flex;
    align-items: center;
    gap: 12px;
}

.step-circle {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.6);
    transition: all 0.3s;
}

.step-item.active   .step-circle { background: #64b5f6; color: #fff; box-shadow: 0 0 20px rgba(100, 181, 246, 0.5); }
.step-item.completed .step-circle { background: #81c784; color: #fff; }

.step-label { font-size: 14px; color: rgba(255, 255, 255, 0.6); }
.step-item.active    .step-label { color: #fff; font-weight: 500; }
.step-item.completed .step-label { color: #a5d6a7; }

.step-connector {
    width: 80px;
    height: 2px;
    background: rgba(255, 255, 255, 0.2);
    margin: 0 20px;
}
.step-connector.completed { background: #81c784; }

/* ─── 主内容区 ─────────────────────────────────────────────────────────────── */
.main-content {
    max-width: 900px;
    margin: 40px auto;
    padding: 0 20px 40px;
}

.section-card {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    overflow: hidden;
}

.section-header {
    padding: 20px 30px;
    border-bottom: 1px solid #eee;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

.section-title {
    font-size: 18px;
    font-weight: 600;
    color: #1a237e;
    display: flex;
    align-items: center;
    gap: 10px;
}
.section-title .el-icon { color: #1976d2; }

.section-body { padding: 30px; }

/* ─── 验证模式 tabs ────────────────────────────────────────────────────────── */
.mode-tabs {
    display: flex;
    gap: 16px;
    margin-bottom: 10px;
}

.mode-tab {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 28px;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: #666;
    background: #fff;
    transition: all 0.3s;
}
.mode-tab:hover { border-color: #1976d2; color: #1976d2; }
.mode-tab.active {
    border-color: #1976d2;
    background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
    color: #fff;
}

/* ─── 表单元素 ─────────────────────────────────────────────────────────────── */
.form-group { margin-bottom: 24px; }

.form-label {
    display: block;
    font-size: 14px;
    font-weight: 500;
    color: #333;
    margin-bottom: 10px;
}

.optional { color: #999; font-weight: normal; font-size: 12px; }

.form-input { width: 100%; }
:deep(.form-input .el-input__wrapper) {
    border-radius: 10px;
    border: 2px solid #e0e0e0;
    box-shadow: none;
}
:deep(.form-input .el-input__wrapper:hover),
:deep(.form-input .el-input__wrapper.is-focus) {
    border-color: #1976d2;
    box-shadow: 0 0 0 4px rgba(25, 118, 210, 0.1);
}

/* ─── 用例树工具栏 ─────────────────────────────────────────────────────────── */
.toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.case-count {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
    border-radius: 10px;
    font-size: 14px;
    color: #1565c0;
    white-space: nowrap;
}

/* ─── 用例树 ───────────────────────────────────────────────────────────────── */
.case-tree-wrap {
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    overflow: hidden;
    min-height: 200px;
    padding: 8px 0;
}

.tree-node-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
}

.node-icon.folder { color: #ffc107; }
.node-icon.file   { color: #1976d2; }

/* ─── 环境配置提示 ─────────────────────────────────────────────────────────── */
.info-tip {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 16px 20px;
    background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
    border-radius: 10px;
    margin-bottom: 24px;
    border-left: 4px solid #ffc107;
}
.tip-icon { color: #f57c00; font-size: 18px; margin-top: 2px; }
.info-tip p { font-size: 14px; color: #666; line-height: 1.6; }

/* ─── 环境卡片 ─────────────────────────────────────────────────────────────── */
.env-cards { display: grid; gap: 16px; }

.env-card {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 20px 24px;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 12px;
    border: 2px solid transparent;
    transition: all 0.3s;
}
.env-card:hover { border-color: #1976d2; box-shadow: 0 4px 16px rgba(25, 118, 210, 0.15); }

.env-icon {
    width: 50px;
    height: 50px;
    background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 22px;
    flex-shrink: 0;
}

.env-info { flex: 1; }
.env-title { font-size: 15px; font-weight: 600; color: #333; margin-bottom: 4px; }
.env-label { font-size: 13px; color: #666; }

.env-input-group { display: flex; align-items: center; gap: 10px; }
.env-input-label { font-size: 13px; color: #666; white-space: nowrap; }

:deep(.env-index-input .el-input__wrapper) {
    border-radius: 8px;
    border: 2px solid #e0e0e0;
    box-shadow: none;
    text-align: center;
}
:deep(.env-index-input .el-input__inner) { text-align: center; }

/* ─── 执行页：配置汇总 ─────────────────────────────────────────────────────── */
.summary-section { margin-bottom: 28px; }

.summary-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #333;
    margin-bottom: 16px;
}
.summary-title .el-icon { color: #1976d2; }

.summary-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    border: 1px solid #eee;
    border-radius: 8px;
    overflow: hidden;
}
.summary-table tr { border-bottom: 1px solid #f0f0f0; }
.summary-table tr:last-child { border-bottom: none; }
.summary-table th {
    padding: 12px 16px;
    text-align: left;
    font-weight: 500;
    color: #666;
    background: #f8f9fa;
    width: 120px;
    vertical-align: top;
}
.summary-table td { padding: 12px 16px; color: #333; }

.summary-cases {
    margin: 0;
    padding-left: 16px;
}
.summary-cases li {
    padding: 4px 0;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    color: #555;
    line-height: 1.5;
}
.no-cases { color: #999; font-size: 13px; }

/* ─── 执行页：日志输出 ─────────────────────────────────────────────────────── */
.log-section { margin-bottom: 28px; }

.log-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #333;
    margin-bottom: 12px;
}
.log-title .el-icon { color: #1976d2; }

.log-output {
    background: #1e1e1e;
    border-radius: 10px;
    padding: 20px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    line-height: 1.8;
    max-height: 280px;
    overflow-y: auto;
}

.log-line       { margin: 0; white-space: pre-wrap; word-break: break-all; }
.log-info    { color: #64b5f6; }
.log-success { color: #81c784; }
.log-error   { color: #e57373; }
.log-warning { color: #ffb74d; }

/* ─── 执行页：结果汇总 ─────────────────────────────────────────────────────── */
.result-section { margin-bottom: 10px; }

.result-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #333;
    margin-bottom: 16px;
}
.result-title .el-icon { color: #1976d2; }

.result-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 20px;
}

.result-card {
    padding: 24px;
    border-radius: 12px;
    text-align: center;
    transition: transform 0.3s;
}
.result-card:hover { transform: translateY(-4px); }

.result-card.success { background: linear-gradient(135deg, #e8f5e9, #c8e6c9); border: 2px solid #81c784; }
.result-card.failed  { background: linear-gradient(135deg, #ffebee, #ffcdd2); border: 2px solid #e57373; }
.result-card.total   { background: linear-gradient(135deg, #e3f2fd, #bbdefb); border: 2px solid #64b5f6; }

.result-icon {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 12px;
    font-size: 20px;
}
.result-icon.success { background: #81c784; color: #fff; }
.result-icon.failed  { background: #e57373; color: #fff; }
.result-icon.total   { background: #64b5f6; color: #fff; }

.result-number { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
.result-number.success { color: #2e7d32; }
.result-number.failed  { color: #c62828; }
.result-number.total   { color: #1565c0; }
.result-label { font-size: 14px; color: #666; }

/* ─── 底部操作按钮 ─────────────────────────────────────────────────────────── */
.footer-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 30px;
    background: #fafafa;
    border-top: 1px solid #eee;
}

.btn-group { display: flex; gap: 12px; }

.btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 32px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s;
    border: none;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-prev {
    background: #fff;
    border: 2px solid #ddd;
    color: #666;
}
.btn-prev:not(:disabled):hover { border-color: #bbb; color: #333; }

.btn-next {
    background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
    color: #fff;
}
.btn-next:hover {
    background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(25, 118, 210, 0.3);
}

.btn-cancel {
    background: #fff;
    border: 2px solid #ddd;
    color: #666;
}
.btn-cancel:not(:disabled):hover { border-color: #e57373; color: #e57373; }

.btn-primary {
    background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
    color: #fff;
}
.btn-primary:not(:disabled):hover {
    background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(25, 118, 210, 0.3);
}

/* 旋转动画（执行中图标） */
.rotating {
    animation: spin 1s linear infinite;
}
@keyframes spin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
}
</style>
