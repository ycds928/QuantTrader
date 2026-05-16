import { lazy } from 'react'

// 懒加载各模块页面
export const HomePage = lazy(() => import('@/api-data/pages/Dashboard'))
export const ApiDataPage = lazy(() => import('@/api-data/pages/ApiData'))
export const SymbolDetailPage = lazy(() => import('@/api-data/pages/SymbolDetail'))
export const AccountPage = lazy(() => import('@/account-trading/pages/Account'))
export const StrategiesPage = lazy(() => import('@/strategy-engine/pages/Strategies'))
export const StrategyEditorPage = lazy(() => import('@/strategy-engine/pages/StrategyEditor'))
export const ExecutionPage = lazy(() => import('@/strategy-execution/pages/Execution'))
export const ReviewPage = lazy(() => import('@/review-analysis/pages/Review'))
export const ReplayPage = lazy(() => import('@/history-replay/pages/Replay'))
