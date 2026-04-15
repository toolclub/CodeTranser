<template>
    <div class="bug-tracker-list">
        <!-- 顶部操作栏 -->
        <div class="top-bar">
            <div class="search-box">
                <el-input
                    v-model="searchKeyword"
                    placeholder="请输入搜索内容……"
                    clearable
                    style="width: 340px"
                    @clear="handleSearch"
                    @keyup.enter="handleSearch"
                >
                    <template #prefix>
                        <el-icon><Search /></el-icon>
                    </template>
                </el-input>
                <el-button @click="handleSearch">
                    <el-icon><Search /></el-icon>
                </el-button>
            </div>
            <el-button type="primary" class="btn-create" @click="goToCreate">
                <el-icon><Plus /></el-icon>
                新增分析
            </el-button>
        </div>

        <!-- 内容区域 -->
        <div class="content-area">
            <h2 class="page-title">构建记录</h2>

            <div class="table-container">
                <el-table
                    v-loading="loading"
                    :data="tableData"
                    style="width: 100%"
                    :header-cell-style="{ background: '#f8f9fa', color: '#495057', fontWeight: '600', fontSize: '13px' }"
                    :cell-style="{ fontSize: '13px', color: '#555' }"
                >
                    <el-table-column prop="taskId" label="任务ID" min-width="110" />
                    <el-table-column prop="mode" label="验证模式" min-width="110" />
                    <el-table-column prop="repoName" label="代码仓库名称" min-width="130" />
                    <el-table-column prop="branch" label="构建分支" min-width="110" />
                    <el-table-column label="commitID" min-width="190">
                        <template #default="{ row }">
                            <span class="commit-id">{{ row.commitId }}</span>
                        </template>
                    </el-table-column>
                    <el-table-column prop="totalCases" label="用例总数" min-width="90" align="center" />
                    <el-table-column prop="successCases" label="成功用例数" min-width="100" align="center" />
                    <el-table-column prop="failedCases" label="失败用例数" min-width="100" align="center" />
                    <el-table-column label="状态" min-width="95" align="center">
                        <template #default="{ row }">
                            <span :class="['status-badge', `status-${row.status}`]">
                                <span v-if="row.status === 'running'" class="pulse-dot" />
                                {{ STATUS_LABELS[row.status] ?? row.status }}
                            </span>
                        </template>
                    </el-table-column>
                    <el-table-column prop="startTime" label="开始执行时间" min-width="160" />
                    <el-table-column label="结束执行时间" min-width="160">
                        <template #default="{ row }">
                            {{ row.endTime || '-' }}
                        </template>
                    </el-table-column>
                    <el-table-column label="操作" width="100" fixed="right" align="center">
                        <template #default="{ row }">
                            <div class="action-btns">
                                <el-tooltip content="重跑" placement="top">
                                    <el-button
                                        :disabled="row.status === 'running' || row.status === 'pending'"
                                        size="small"
                                        circle
                                        class="btn-rerun"
                                        @click="handleRerun(row)"
                                    >
                                        <el-icon><RefreshRight /></el-icon>
                                    </el-button>
                                </el-tooltip>
                                <el-tooltip content="删除" placement="top">
                                    <el-button
                                        size="small"
                                        circle
                                        class="btn-delete"
                                        @click="handleDelete(row)"
                                    >
                                        <el-icon><Delete /></el-icon>
                                    </el-button>
                                </el-tooltip>
                            </div>
                        </template>
                    </el-table-column>
                </el-table>

                <!-- 分页 -->
                <div class="pagination-wrapper">
                    <span class="pagination-info">总计：{{ pagination.total }}</span>
                    <el-pagination
                        v-model:current-page="pagination.page"
                        v-model:page-size="pagination.pageSize"
                        :total="pagination.total"
                        :page-sizes="[10, 20, 50]"
                        layout="prev, pager, next, sizes"
                        background
                        @current-change="loadData"
                        @size-change="loadData"
                    />
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, RefreshRight, Delete } from '@element-plus/icons-vue'
import { getBuildRecordList, deleteBuildRecord, rerunTask } from '@/api/bugTracker/index'

const router = useRouter()

// ─── 状态映射 ────────────────────────────────────────────────────────────────
const STATUS_LABELS = {
    success: '成功',
    running: '运行中',
    failed:  '失败',
    pending: '待执行',
}

// ─── 响应式数据 ───────────────────────────────────────────────────────────────
const loading        = ref(false)
const searchKeyword  = ref('')
const tableData      = ref([])
const pagination     = reactive({ page: 1, pageSize: 10, total: 0 })

// ─── 数据加载 ─────────────────────────────────────────────────────────────────
async function loadData() {
    loading.value = true
    try {
        /**
         * TODO: 接口联调后删除 mock 数据，改为真实请求
         *
         * const res = await getBuildRecordList({
         *   page: pagination.page,
         *   pageSize: pagination.pageSize,
         *   keyword: searchKeyword.value,
         * })
         * tableData.value   = res.list
         * pagination.total  = res.total
         */

        // ── Mock 数据（接口就绪后删除） ──────────────────────────────────────
        await new Promise(r => setTimeout(r, 400))
        tableData.value = [
            { taskId: 'TAS1567', mode: '单节点验证', repoName: 'GitHub仓库A', branch: 'dev-nginx',    commitId: 'commit_123456',                          totalCases: 125, successCases: 120, failedCases: 5, status: 'success', startTime: '2023-05-08 09:00:00', endTime: '2023-05-08 14:32:00' },
            { taskId: 'task5668', mode: '多节点验证', repoName: 'GitHub仓库B', branch: 'feature-new', commitId: 'commit_664321~commit_987654',             totalCases: 123, successCases: 75,  failedCases: 3, status: 'running', startTime: '2023-05-09 10:15:00', endTime: '' },
            { taskId: 'TAS1568', mode: '单节点验证', repoName: 'GitHub仓库C', branch: 'hotfix-bug',   commitId: 'commit_555666',                          totalCases: 98,  successCases: 98,  failedCases: 0, status: 'success', startTime: '2023-05-10 08:30:00', endTime: '2023-05-10 12:45:00' },
            { taskId: 'task5669', mode: '多节点验证', repoName: 'GitHub仓库A', branch: 'release-v2',  commitId: 'commit_111222~commit_333444',             totalCases: 156, successCases: 0,   failedCases: 0, status: 'pending', startTime: '', endTime: '' },
            { taskId: 'TAS1569', mode: '单节点验证', repoName: 'GitHub仓库D', branch: 'dev-api',      commitId: 'commit_789012',                          totalCases: 87,  successCases: 82,  failedCases: 5, status: 'failed',  startTime: '2023-05-11 14:00:00', endTime: '2023-05-11 18:30:00' },
            { taskId: 'task5670', mode: '单节点验证', repoName: 'GitHub仓库B', branch: 'test-ci',     commitId: 'commit_345678',                          totalCases: 110, successCases: 108, failedCases: 2, status: 'success', startTime: '2023-05-12 09:30:00', endTime: '2023-05-12 15:00:00' },
            { taskId: 'TAS1570', mode: '多节点验证', repoName: 'GitHub仓库E', branch: 'feature-auth', commitId: 'commit_456789~commit_567890',             totalCases: 145, successCases: 140, failedCases: 5, status: 'running', startTime: '2023-05-13 11:00:00', endTime: '' },
            { taskId: 'task5671', mode: '单节点验证', repoName: 'GitHub仓库A', branch: 'main',        commitId: 'commit_999888',                          totalCases: 92,  successCases: 90,  failedCases: 2, status: 'success', startTime: '2023-05-14 08:00:00', endTime: '2023-05-14 13:20:00' },
        ]
        pagination.total = 10
        // ────────────────────────────────────────────────────────────────────
    } catch {
        ElMessage.error('获取构建记录失败')
    } finally {
        loading.value = false
    }
}

function handleSearch() {
    pagination.page = 1
    loadData()
}

// ─── 操作 ─────────────────────────────────────────────────────────────────────
async function handleRerun(row) {
    try {
        // TODO: await rerunTask(row.taskId)
        ElMessage.success(`任务 ${row.taskId} 已重新提交`)
        loadData()
    } catch {
        ElMessage.error('重跑失败')
    }
}

async function handleDelete(row) {
    await ElMessageBox.confirm(`确定删除任务 ${row.taskId}？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText:  '取消',
        type: 'warning',
    })
    try {
        // TODO: await deleteBuildRecord(row.taskId)
        ElMessage.success('删除成功')
        loadData()
    } catch {
        ElMessage.error('删除失败')
    }
}

function goToCreate() {
    router.push({ name: 'BugTrackerCreate' })
}

onMounted(loadData)
</script>

<style scoped>
.bug-tracker-list {
    min-height: 100vh;
    background: #f5f7fa;
}

/* 顶部操作栏 */
.top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 30px;
    background: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    position: sticky;
    top: 0;
    z-index: 50;
}

.search-box {
    display: flex;
    align-items: center;
    gap: 10px;
}

.btn-create {
    background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
    border: none;
    font-weight: 500;
}
.btn-create:hover {
    background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
}

/* 内容区域 */
.content-area {
    padding: 25px 30px;
}

.page-title {
    font-size: 20px;
    font-weight: 600;
    color: #1a237e;
    margin-bottom: 20px;
}

/* 表格容器 */
.table-container {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
    overflow: hidden;
}

/* commitID 样式 */
.commit-id {
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    background: #f5f5f5;
    padding: 2px 6px;
    border-radius: 4px;
    color: #666;
}

/* 状态标签 */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
}

.status-success { background: #e8f5e9; color: #2e7d32; }
.status-running  { background: #e3f2fd; color: #1565c0; }
.status-failed   { background: #ffebee; color: #c62828; }
.status-pending  { background: #fff3e0; color: #ef6c00; }

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

/* 操作按钮 */
.action-btns {
    display: flex;
    gap: 6px;
    justify-content: center;
}

.btn-rerun {
    background: #e3f2fd;
    border-color: #e3f2fd;
    color: #1976d2;
}
.btn-rerun:not(:disabled):hover {
    background: #1976d2;
    border-color: #1976d2;
    color: #fff;
}

.btn-delete {
    background: #ffebee;
    border-color: #ffebee;
    color: #e53935;
}
.btn-delete:hover {
    background: #e53935;
    border-color: #e53935;
    color: #fff;
}

/* 分页 */
.pagination-wrapper {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    background: #fafafa;
    border-top: 1px solid #eee;
}

.pagination-info {
    font-size: 13px;
    color: #666;
}
</style>
