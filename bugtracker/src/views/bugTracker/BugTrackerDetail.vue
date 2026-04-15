<template>
    <div class="bug-tracker-detail">
        <!-- 顶部导航栏 -->
        <div class="top-bar">
            <button class="back-btn" @click="router.push({ name: 'BugTrackerList' })">
                <el-icon><ArrowLeft /></el-icon>
                返回列表
            </button>
            <h1 class="page-title">任务详情</h1>
            <div v-if="taskDetail" class="task-id-badge">
                <span class="badge-label">任务ID</span>
                <span class="badge-value">{{ taskDetail.taskId }}</span>
            </div>
        </div>

        <!-- 步骤导航（只读，仅展示完成状态） -->
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

        <!-- 加载状态 -->
        <div v-if="loading" class="loading-wrap">
            <el-icon class="is-loading" style="font-size: 32px; color: #1976d2">
                <Loading />
            </el-icon>
            <p style="margin-top: 12px; color: #666">正在加载任务详情…</p>
        </div>

        <!-- 主内容区 -->
        <div v-else-if="taskDetail" class="main-content">
            <div class="section-card">
                <!-- ══════════════════ STEP 1：基础配置（只读） ══════════════════ -->
                <div class="section-header">
                    <h2 class="section-title">
                        <el-icon><Setting /></el-icon>
                        基础配置
                    </h2>
                </div>
                <div class="section-body">
                    <table class="summary-table">
                        <tbody>
                            <tr>
                                <th>验证模式</th>
                                <td>{{ taskDetail.mode === 'single' ? '单节点验证' : '多节点验证' }}</td>
                            </tr>
                            <tr>
                                <th>代码仓库</th>
                                <td>{{ taskDetail.repo }}</td>
                            </tr>
                            <tr>
                                <th>目标分支</th>
                                <td>{{ taskDetail.branch }}</td>
                            </tr>
                            <tr>
                                <th>commit 节点</th>
                                <td>
                                    <span v-if="taskDetail.mode === 'single'">
                                        {{ taskDetail.commitId || '（使用最新 commit）' }}
                                    </span>
                                    <span v-else>
                                        {{ taskDetail.startCommitId }} ~ {{ taskDetail.endCommitId }}
                                    </span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- ══════════════════ STEP 2：用例配置（只读） ══════════════════ -->
                <div class="section-header">
                    <h2 class="section-title">
                        <el-icon><List /></el-icon>
                        用例配置
                    </h2>
                </div>
                <div class="section-body">
                    <div class="case-count-bar">
                        <el-icon><Select /></el-icon>
                        共 <strong>{{ taskDetail.selectedCases?.length ?? 0 }}</strong> 个用例
                    </div>
                    <div class="case-list-wrap">
                        <div
                            v-for="c in taskDetail.selectedCases"
                            :key="c.id"
                            class="case-item"
                        >
                            <el-icon class="case-icon"><Document /></el-icon>
                            {{ c.label }}
                        </div>
                    </div>
                </div>

                <!-- ══════════════════ STEP 3：环境配置（只读） ══════════════════ -->
                <div class="section-header">
                    <h2 class="section-title">
                        <el-icon><Cpu /></el-icon>
                        环境配置
                    </h2>
                </div>
                <div class="section-body">
                    <div class="env-cards">
                        <div v-for="env in taskDetail.environments" :key="env.id" class="env-card">
                            <div class="env-icon">
                                <el-icon><Monitor /></el-icon>
                            </div>
                            <div class="env-info">
                                <div class="env-title">{{ env.name }}</div>
                                <div class="env-label">{{ env.label }}</div>
                            </div>
                            <div class="env-index-display">
                                <span class="env-index-label">环境序号</span>
                                <span class="env-index-value">{{ env.envIndex }}</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ══════════════════ STEP 4：执行操作（只读） ══════════════════ -->
                <div class="section-header">
                    <h2 class="section-title">
                        <el-icon><VideoPlay /></el-icon>
                        执行操作
                    </h2>
                    <div v-if="taskDetail.status === 'running'" class="status-running-tag">
                        <span class="pulse-dot" />
                        执行中…
                    </div>
                    <div v-else-if="taskDetail.status === 'success'" class="status-success-tag">成功</div>
                    <div v-else-if="taskDetail.status === 'failed'"  class="status-failed-tag">失败</div>
                    <div v-else class="status-pending-tag">待执行</div>
                </div>
                <div class="section-body">
                    <!-- 日志输出（执行后或执行中实时滚动） -->
                    <div class="log-section">
                        <div class="log-title">
                            <el-icon><DataLine /></el-icon>
                            日志输出
                        </div>
                        <div ref="logBoxRef" class="log-output">
                            <p
                                v-for="(line, i) in logLines"
                                :key="i"
                                :class="['log-line', logLineClass(line)]"
                            >{{ line }}</p>
                            <p v-if="!logLines.length && taskDetail.status === 'pending'" class="log-line log-info">
                                [INFO] 等待执行，暂无日志…
                            </p>
                        </div>
                    </div>

                    <!-- 结果汇总（执行完成后显示） -->
                    <div v-if="taskDetail.status !== 'pending' && taskDetail.status !== 'running'" class="result-section">
                        <div class="result-title">
                            <el-icon><PieChart /></el-icon>
                            结果汇总
                        </div>
                        <div class="result-cards">
                            <div class="result-card success">
                                <div class="result-icon success"><el-icon><Check /></el-icon></div>
                                <div class="result-number success">{{ taskDetail.result?.success ?? '-' }}</div>
                                <div class="result-label">成功用例</div>
                            </div>
                            <div class="result-card failed">
                                <div class="result-icon failed"><el-icon><Close /></el-icon></div>
                                <div class="result-number failed">{{ taskDetail.result?.failed ?? '-' }}</div>
                                <div class="result-label">失败用例</div>
                            </div>
                            <div class="result-card total">
                                <div class="result-icon total"><el-icon><List /></el-icon></div>
                                <div class="result-number total">{{ taskDetail.result?.total ?? '-' }}</div>
                                <div class="result-label">总用例数</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 底部：前翻 / 后翻（只读浏览，不编辑） -->
                <div class="footer-actions">
                    <button
                        class="btn btn-prev"
                        :disabled="currentReadStep <= 1"
                        @click="currentReadStep--"
                    >
                        <el-icon><ArrowLeft /></el-icon>
                        上一步
                    </button>
                    <span class="step-hint">第 {{ currentReadStep }} / 4 步，仅供查看</span>
                    <button
                        class="btn btn-next"
                        :disabled="currentReadStep >= 4"
                        @click="currentReadStep++"
                    >
                        下一步
                        <el-icon><ArrowRight /></el-icon>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
    ArrowLeft, ArrowRight, Check, Close, Setting, Monitor,
    List, Document, Cpu, VideoPlay, DataLine, PieChart,
    Select, Loading,
} from '@element-plus/icons-vue'
import { getTaskDetailObj, getTaskLogsObj } from '@/api/bugTracker/business'

const router = useRouter()
const route  = useRoute()

// ─── 步骤定义 ────────────────────────────────────────────────────────────────
const STEPS = [
    { key: 'basic', label: '基础配置' },
    { key: 'case',  label: '用例配置' },
    { key: 'env',   label: '环境配置' },
    { key: 'exec',  label: '执行操作' },
]

const taskId = computed(() => route.query.taskId)

// ─── 数据 ────────────────────────────────────────────────────────────────────
const loading       = ref(false)
const taskDetail    = ref(null)
const currentReadStep = ref(4) // 默认落在第4步

let pollTimer  = null
let logOffset  = 0
const logLines = ref([])

// ─── 步骤状态（固定为已完成，用于展示） ───────────────────────────────────────
function stepState(n) {
    if (n < 4) return 'completed'
    if (n === 4) return 'active'
    return 'inactive'
}

// ─── 日志颜色 ────────────────────────────────────────────────────────────────
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

// ─── 轮询日志 ────────────────────────────────────────────────────────────────
async function pollLogs() {
    if (!taskId.value) return
    try {
        /**
         * TODO: 接口就绪后替换
         * const res = await getTaskLogsObj({ taskId: taskId.value, offset: logOffset })
         * logLines.value.push(...res.lines)
         * logOffset += res.lines.length
         * scrollLogToBottom()
         * if (!res.hasMore) stopPolling()
         */

        // ── Mock 日志（接口就绪后删除） ─────────────────────────────────────
        await new Promise(r => setTimeout(r, 600))
        const mock = [
            `[INFO]  ${time()} 开始执行用例：TC_LOG_NORMAL_RECORD_FUNC_004`,
            `[SUCCESS] ${time()} TC_LOG_NORMAL_RECORD_FUNC_004 - 用例执行通过`,
            `[INFO]  ${time()} 开始执行用例：TC_ETH_LANSWITCH_PORT_FUNC_016`,
            `[SUCCESS] ${time()} TC_ETH_LANSWITCH_PORT_FUNC_016 - 用例执行通过`,
            `[INFO]  ${time()} 开始执行用例：3920R1`,
            `[ERROR]  ${time()} 3920R1 - 用例执行失败：断言失败`,
            `[INFO]  ${time()} 开始执行用例：RootBBU`,
            `[SUCCESS] ${time()} RootBBU - 用例执行通过`,
            `[INFO]  ${time()} 所有用例执行完成`,
            `[SUCCESS] ${time()} 测试报告已生成：report-${date()}.html`,
        ]
        const batch = mock.slice(logOffset, logOffset + 2)
        logLines.value.push(...batch)
        logOffset += batch.length
        scrollLogToBottom()
        if (logOffset >= mock.length) stopPolling()
        // ───────────────────────────────────────────────────────────────────
    } catch {
        stopPolling()
    }
}

function stopPolling() {
    clearInterval(pollTimer)
    pollTimer = null
}

// ─── 加载任务详情 ────────────────────────────────────────────────────────────
async function loadDetail() {
    if (!taskId.value) {
        ElMessage.error('缺少 taskId 参数')
        router.push({ name: 'BugTrackerList' })
        return
    }
    loading.value = true
    try {
        /**
         * TODO: 接口就绪后替换
         * const res = await getTaskDetailObj({ taskId: taskId.value })
         * taskDetail.value = res
         * if (res.logLines) logLines.value = res.logLines
         */

        // ── Mock 详情（接口就绪后删除） ──────────────────────────────────────
        await new Promise(r => setTimeout(r, 600))
        taskDetail.value = {
            taskId: taskId.value,
            status: 'running',
            mode: 'single',
            repo: 'TRAN_xxx/xxx',
            branch: 'v5r18c00_master',
            commitId: '12dd10b443e66ae5c8fdc7aa3f409f7c4c9e7a1615',
            startCommitId: '',
            endCommitId: '',
            selectedCases: [
                { id: 'TC_LOG_NORMAL_RECORD_FUNC_004',   label: 'TC_LOG_NORMAL_RECORD_FUNC_004' },
                { id: 'TC_ETH_LANSWITCH_PORT_FUNC_016',  label: 'TC_ETH_LANSWITCH_PORT_FUNC_016' },
                { id: 'TC_NETWORKKLv4_PROADDR_STATS_IPSTAT_FUNC_001', label: 'TC_NETWORKKLv4_PROADDR_STATS_IPSTAT_FUNC_001' },
                { id: 'TC_NETWORKLV6_ADDRESS_MANAGE_LIMIT_001',       label: 'TC_NETWORKLV6_ADDRESS_MANAGE_LIMIT_001' },
                { id: 'TC_SECU_IPSECV4_VPNSA_AUTO_FUNC_063',          label: 'TC_SECU_IPSECV4_VPNSA_AUTO_FUNC_063' },
            ],
            environments: [
                { id: 'env1', name: 'FO1_UMPTB_TOPO1_NEW',            label: 'UMPTB 物理拓扑环境',        envIndex: '107' },
                { id: 'env2', name: 'FO3_UMPTEC05_TOPO1_NEW',          label: 'UMPTEC05 物理拓扑环境',      envIndex: '310' },
                { id: 'env3', name: 'FO5_UMPPTH_UMPTG_TOPO2_LB2',      label: 'UMPPTH+UMPTG 组合拓扑环境',  envIndex: '544' },
            ],
            result: null,
        }
        // ──────────────────────────────────────────────────────────────────
    } catch {
        ElMessage.error('获取任务详情失败')
    } finally {
        loading.value = false
    }
}

function time() {
    return new Date().toTimeString().slice(0, 8)
}
function date() {
    return new Date().toISOString().slice(0, 10).replace(/-/g, '')
}

const logBoxRef = ref(null)

// ─── 启动 / 停止轮询 ────────────────────────────────────────────────────────
watch(taskDetail, (detail) => {
    if (!detail) return
    if (detail.status === 'running' || detail.status === 'pending') {
        logOffset  = detail.logLines?.length ?? 0
        logLines.value = [...(detail.logLines ?? [])]
        stopPolling()
        pollTimer = setInterval(pollLogs, 2000)
    } else {
        logLines.value = [...(detail.logLines ?? [])]
        stopPolling()
    }
}, { immediate: true })

onMounted(loadDetail)
onUnmounted(stopPolling)
</script>

<style scoped>
/* ─── 整体布局 ─────────────────────────────────────────────────────────────── */
.bug-tracker-detail {
    min-height: 100vh;
    background: #f0f2f5;
}

/* ─── 顶部导航栏 ─────────────────────────────────────────────────────────── */
.top-bar {
    display: flex;
    align-items: center;
    gap: 20px;
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
    transition: all 0.2s;
}
.back-btn:hover { background: #eee; color: #333; }

.page-title {
    font-size: 18px;
    font-weight: 600;
    color: #1a237e;
    flex: 1;
}

.task-id-badge {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 16px;
    background: #e8eaf6;
    border-radius: 8px;
    border: 1px solid #c5cae9;
}
.badge-label { font-size: 12px; color: #666; }
.badge-value { font-family: 'Consolas', monospace; font-size: 14px; font-weight: 600; color: #1a237e; }

/* ─── 步骤导航 ─────────────────────────────────────────────────────────────── */
.step-navigation {
    background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
    padding: 36px 60px;
    display: flex;
    justify-content: center;
    align-items: center;
}

.step-item { display: flex; align-items: center; gap: 12px; }

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

.step-item.active    .step-circle { background: #64b5f6; color: #fff; box-shadow: 0 0 20px rgba(100, 181, 246, 0.5); }
.step-item.completed .step-circle { background: #81c784; color: #fff; }

.step-label          { font-size: 14px; color: rgba(255, 255, 255, 0.6); }
.step-item.active    .step-label { color: #fff; font-weight: 500; }
.step-item.completed .step-label { color: #a5d6a7; }

.step-connector {
    width: 80px;
    height: 2px;
    background: rgba(255, 255, 255, 0.2);
    margin: 0 20px;
}
.step-connector.completed { background: #81c784; }

/* ─── 加载状态 ───────────────────────────────────────────────────────────── */
.loading-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 300px;
}

/* ─── 主内容区 ───────────────────────────────────────────────────────────── */
.main-content {
    max-width: 900px;
    margin: 40px auto;
    padding: 0 20px 60px;
}

.section-card {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    overflow: hidden;
    margin-bottom: 24px;
}

.section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 30px;
    border-bottom: 1px solid #eee;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

.section-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 18px;
    font-weight: 600;
    color: #1a237e;
}
.section-title .el-icon { color: #1976d2; }

.section-body { padding: 30px; }

/* ─── 状态标签 ───────────────────────────────────────────────────────────── */
.status-running-tag {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    background: #e3f2fd;
    color: #1565c0;
}
.pulse-dot {
    width: 6px;
    height: 6px;
    background: currentColor;
    border-radius: 50%;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
}

.status-success-tag { padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; background: #e8f5e9; color: #2e7d32; }
.status-failed-tag  { padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; background: #ffebee; color: #c62828; }
.status-pending-tag { padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; background: #fff3e0; color: #ef6c00; }

/* ─── 汇总表格 ───────────────────────────────────────────────────────────── */
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
}
.summary-table td { padding: 12px 16px; color: #333; }

/* ─── 用例列表 ───────────────────────────────────────────────────────────── */
.case-count-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: #e8eaf6;
    border-radius: 8px;
    font-size: 14px;
    color: #1a237e;
    margin-bottom: 16px;
}

.case-list-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.case-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    background: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    font-size: 12px;
    font-family: 'Consolas', monospace;
    color: #555;
}
.case-icon { color: #1976d2; font-size: 12px; }

/* ─── 环境卡片 ───────────────────────────────────────────────────────────── */
.env-cards { display: grid; gap: 16px; }

.env-card {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 20px 24px;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 12px;
    border: 2px solid transparent;
}

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

.env-index-display {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 8px 16px;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
}
.env-index-label { font-size: 11px; color: #999; }
.env-index-value { font-size: 18px; font-weight: 700; color: #1976d2; font-family: 'Consolas', monospace; }

/* ─── 日志输出 ───────────────────────────────────────────────────────────── */
.log-section { margin-bottom: 24px; }

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

/* ─── 结果汇总 ───────────────────────────────────────────────────────────── */
.result-section { }

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
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
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
    color: #fff;
}
.result-icon.success { background: #81c784; }
.result-icon.failed  { background: #e57373; }
.result-icon.total   { background: #64b5f6; }

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

.step-hint {
    font-size: 12px;
    color: #999;
    font-style: italic;
}

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
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

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
.btn-next:not(:disabled):hover {
    background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(25, 118, 210, 0.3);
}
</style>
