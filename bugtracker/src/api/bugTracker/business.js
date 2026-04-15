/**
 * BugTracker 业务层
 * 按项目约定用 default_business_handle_logic 包装原始接口，
 * 页面组件统一从此文件 import。
 *
 * TODO: 将下方 default_business_handle_logic 的引入路径改为项目实际路径
 *       例如: import { default_business_handle_logic } from '@/core/com'
 *             import { default_business_handle_logic } from '@/api/com'
 */
import { default_business_handle_logic } from '@/core/com'
import { bugTrackerApi } from './index'

const BUSINESS_ERROR_MSG = {
    getBuildRecordList:    '获取构建记录列表失败',
    deleteBuildRecord:     '删除构建记录失败',
    rerunTask:             '重跑任务失败',
    getCaseTree:           '获取用例列表失败',
    getMatchedEnvironments:'获取环境配置失败',
    createAnalysisTask:    '提交分析任务失败',
    getTaskLogs:           '获取执行日志失败',
    getTaskResult:         '获取执行结果失败',
    getTaskDetail:         '获取任务详情失败',
}

const DEFAULT_HEADERS = { 'Content-Type': 'application/json' }

/** 获取构建记录列表 */
export const getBuildRecordListObj = (params, headers = DEFAULT_HEADERS) =>
    default_business_handle_logic(bugTrackerApi.getBuildRecordList, BUSINESS_ERROR_MSG.getBuildRecordList, params, headers)

/** 删除构建记录 */
export const deleteBuildRecordObj = (params, headers = DEFAULT_HEADERS) =>
    default_business_handle_logic(bugTrackerApi.deleteBuildRecord, BUSINESS_ERROR_MSG.deleteBuildRecord, params, headers)

/** 重跑任务 */
export const rerunTaskObj = (params, headers = DEFAULT_HEADERS) =>
    default_business_handle_logic(bugTrackerApi.rerunTask, BUSINESS_ERROR_MSG.rerunTask, params, headers)

/** 获取用例树形结构 */
export const getCaseTreeObj = (params, headers = DEFAULT_HEADERS) =>
    default_business_handle_logic(bugTrackerApi.getCaseTree, BUSINESS_ERROR_MSG.getCaseTree, params, headers)

/** 根据已选用例获取匹配环境 */
export const getMatchedEnvironmentsObj = (params, headers = DEFAULT_HEADERS) =>
    default_business_handle_logic(bugTrackerApi.getMatchedEnvironments, BUSINESS_ERROR_MSG.getMatchedEnvironments, params, headers)

/** 创建并提交分析任务 */
export const createAnalysisTaskObj = (params, headers = DEFAULT_HEADERS) =>
    default_business_handle_logic(bugTrackerApi.createAnalysisTask, BUSINESS_ERROR_MSG.createAnalysisTask, params, headers)

/** 轮询获取任务执行日志 */
export const getTaskLogsObj = (params, headers = DEFAULT_HEADERS) =>
    default_business_handle_logic(bugTrackerApi.getTaskLogs, BUSINESS_ERROR_MSG.getTaskLogs, params, headers)

/** 获取任务执行结果汇总 */
export const getTaskResultObj = (params, headers = DEFAULT_HEADERS) =>
    default_business_handle_logic(bugTrackerApi.getTaskResult, BUSINESS_ERROR_MSG.getTaskResult, params, headers)

/** 获取任务完整详情（只读详情页使用） */
export const getTaskDetailObj = (params, headers = DEFAULT_HEADERS) =>
    default_business_handle_logic(bugTrackerApi.getTaskDetail, BUSINESS_ERROR_MSG.getTaskDetail, params, headers)
