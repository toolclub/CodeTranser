import { buildMicroServiceAxiosInstance } from '@/core/axios.promise'

const service = buildMicroServiceAxiosInstance('/mirco_service_gw/')

/**
 * BugTracker 原始接口定义
 * 使用方式：从 business.js 引入包装后的函数，不要直接调用此对象
 */
export const bugTrackerApi = {
    /**
     * 获取构建记录列表
     * GET /bugtracker/api/v1/tasks
     * @param {{ page: number, pageSize: number, keyword?: string }} params
     */
    getBuildRecordList: (params, headers) =>
        service.get('/bugtracker/api/v1/tasks', params, headers),

    /**
     * 删除构建记录
     * DELETE /bugtracker/api/v1/tasks/{taskId}
     */
    deleteBuildRecord: (params, headers) =>
        service.delete(`/bugtracker/api/v1/tasks/${params.taskId}`, params, headers),

    /**
     * 重跑任务
     * POST /bugtracker/api/v1/tasks/{taskId}/rerun
     */
    rerunTask: (params, headers) =>
        service.post(`/bugtracker/api/v1/tasks/${params.taskId}/rerun`, params, headers),

    /**
     * 获取用例树形结构（根据仓库和分支）
     * GET /bugtracker/api/v1/cases/tree
     * @param {{ repo: string, branch: string }} params
     * @returns 树形节点数组，每节点: { id, label, children?, isLeaf? }
     */
    getCaseTree: (params, headers) =>
        service.get('/bugtracker/api/v1/cases/tree', params, headers),

    /**
     * 根据已选用例获取匹配的环境配置
     * POST /bugtracker/api/v1/environments/match
     * @param {{ selectedCaseIds: string[] }} params
     * @returns [{ id, name, label, envIndex }]
     */
    getMatchedEnvironments: (params, headers) =>
        service.post('/bugtracker/api/v1/environments/match', params, headers),

    /**
     * 创建并提交分析任务
     * POST /bugtracker/api/v1/tasks
     * @param {{
     *   mode: 'single'|'multi',
     *   repo: string,
     *   branch: string,
     *   commitId?: string,
     *   startCommitId?: string,
     *   endCommitId?: string,
     *   selectedCaseIds: string[],
     *   environments: { id: string, envIndex: string }[]
     * }} params
     * @returns {{ taskId: string }}
     */
    createAnalysisTask: (params, headers) =>
        service.post('/bugtracker/api/v1/tasks', params, headers),

    /**
     * 轮询获取任务执行日志（增量拉取）
     * GET /bugtracker/api/v1/tasks/{taskId}/logs
     * @param {{ taskId: string, offset: number }} params
     * @returns {{ lines: string[], hasMore: boolean, status: 'running'|'success'|'failed' }}
     */
    getTaskLogs: (params, headers) =>
        service.get(`/bugtracker/api/v1/tasks/${params.taskId}/logs`, { offset: params.offset }, headers),

    /**
     * 获取任务执行结果汇总
     * GET /bugtracker/api/v1/tasks/{taskId}/result
     * @param {{ taskId: string }} params
     * @returns {{ total: number, success: number, failed: number }}
     */
    getTaskResult: (params, headers) =>
        service.get(`/bugtracker/api/v1/tasks/${params.taskId}/result`, params, headers),

    /**
     * 获取任务完整详情（用于只读详情页）
     * GET /bugtracker/api/v1/tasks/{taskId}/detail
     * @param {{ taskId: string }} params
     * @returns {{
     *   taskId: string,
     *   status: 'pending'|'running'|'success'|'failed',
     *   mode: 'single'|'multi',
     *   repo: string,
     *   branch: string,
     *   commitId?: string,
     *   startCommitId?: string,
     *   endCommitId?: string,
     *   selectedCases: { id: string, label: string }[],
     *   environments: { id: string, name: string, label: string, envIndex: string }[],
     *   logLines: string[],
     *   result: { total: number, success: number, failed: number }
     * }}
     */
    getTaskDetail: (params, headers) =>
        service.get(`/bugtracker/api/v1/tasks/${params.taskId}/detail`, params, headers),
}
