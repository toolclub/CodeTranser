import request from '@/core/axios.promise'

/**
 * 获取构建记录列表
 * @param {Object} params - { page: number, pageSize: number, keyword: string }
 * @returns {Promise<{ list: Array, total: number }>}
 *
 * TODO: 接口路径待补全
 * GET /mirco_service_gw/bugtracker/api/v1/tasks
 */
export function getBuildRecordList(params) {
    return request({
        url: '/mirco_service_gw/bugtracker/api/v1/tasks',
        method: 'get',
        params,
    })
}

/**
 * 删除构建记录
 * @param {string} taskId - 任务ID
 * @returns {Promise}
 *
 * TODO: 接口路径待补全
 * DELETE /mirco_service_gw/bugtracker/api/v1/tasks/{taskId}
 */
export function deleteBuildRecord(taskId) {
    return request({
        url: `/mirco_service_gw/bugtracker/api/v1/tasks/${taskId}`,
        method: 'delete',
    })
}

/**
 * 重跑任务
 * @param {string} taskId - 任务ID
 * @returns {Promise}
 *
 * TODO: 接口路径待补全
 * POST /mirco_service_gw/bugtracker/api/v1/tasks/{taskId}/rerun
 */
export function rerunTask(taskId) {
    return request({
        url: `/mirco_service_gw/bugtracker/api/v1/tasks/${taskId}/rerun`,
        method: 'post',
    })
}

/**
 * 获取用例树形结构（根据仓库和分支查询）
 * @param {Object} params - { repo: string, branch: string }
 * @returns {Promise<Array>} 树形节点数组，每个节点 { id, label, children?, isLeaf? }
 *
 * TODO: 接口路径待补全
 * GET /mirco_service_gw/bugtracker/api/v1/cases/tree
 */
export function getCaseTree(params) {
    return request({
        url: '/mirco_service_gw/bugtracker/api/v1/cases/tree',
        method: 'get',
        params,
    })
}

/**
 * 根据已选用例获取匹配的环境配置列表
 * @param {Object} data - { selectedCaseIds: string[] }
 * @returns {Promise<Array>} 环境列表，每项 { id, name, label, icon, envIndex }
 *
 * TODO: 接口路径待补全
 * POST /mirco_service_gw/bugtracker/api/v1/environments/match
 */
export function getMatchedEnvironments(data) {
    return request({
        url: '/mirco_service_gw/bugtracker/api/v1/environments/match',
        method: 'post',
        data,
    })
}

/**
 * 创建并提交分析任务
 * @param {Object} data
 * @param {string}   data.mode           - 验证模式: 'single' | 'multi'
 * @param {string}   data.repo           - 代码仓库
 * @param {string}   data.branch         - 目标分支
 * @param {string}   [data.commitId]     - 单节点 Commit ID（可选）
 * @param {string}   [data.startCommitId] - 多节点起始 Commit ID
 * @param {string}   [data.endCommitId]   - 多节点结束 Commit ID
 * @param {string[]} data.selectedCaseIds - 已选用例 ID 列表
 * @param {Array}    data.environments   - 环境配置列表 [{ id, envIndex }]
 * @returns {Promise<{ taskId: string }>}
 *
 * TODO: 接口路径待补全
 * POST /mirco_service_gw/bugtracker/api/v1/tasks
 */
export function createAnalysisTask(data) {
    return request({
        url: '/mirco_service_gw/bugtracker/api/v1/tasks',
        method: 'post',
        data,
    })
}

/**
 * 轮询获取任务执行日志（增量拉取）
 * @param {string} taskId  - 任务ID
 * @param {number} offset  - 已接收的日志行数，用于增量拉取
 * @returns {Promise<{ lines: string[], hasMore: boolean, status: string }>}
 *   lines   - 新增日志行（每行格式示例: "[INFO] 17:46:28 ..."）
 *   hasMore - 任务是否仍在执行
 *   status  - 任务当前状态: 'running' | 'success' | 'failed'
 *
 * TODO: 接口路径待补全
 * GET /mirco_service_gw/bugtracker/api/v1/tasks/{taskId}/logs?offset={offset}
 */
export function getTaskLogs(taskId, offset = 0) {
    return request({
        url: `/mirco_service_gw/bugtracker/api/v1/tasks/${taskId}/logs`,
        method: 'get',
        params: { offset },
    })
}

/**
 * 获取任务执行结果汇总
 * @param {string} taskId - 任务ID
 * @returns {Promise<{ total: number, success: number, failed: number }>}
 *
 * TODO: 接口路径待补全
 * GET /mirco_service_gw/bugtracker/api/v1/tasks/{taskId}/result
 */
export function getTaskResult(taskId) {
    return request({
        url: `/mirco_service_gw/bugtracker/api/v1/tasks/${taskId}/result`,
        method: 'get',
    })
}
