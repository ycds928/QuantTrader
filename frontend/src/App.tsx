import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Suspense } from 'react'
import {
  HomePage,
  ApiDataPage,
  SymbolDetailPage,
  AccountManagementPage,
  TradingDeskPage,
  OrderQueryPage,
  StrategiesPage,
  StrategyEditorPage,
  ExecutionPage,
  ReviewPage,
  ReplayPage,
} from '@/common/router/routes'

function Loading() {
  return (
    <div className="flex items-center justify-center h-screen bg-background text-on-surface-variant text-sm">
      加载中...
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/api-data" element={<ApiDataPage />} />
          <Route path="/symbol-detail" element={<SymbolDetailPage />} />
          <Route path="/account" element={<AccountManagementPage />} />
          <Route path="/account/manage" element={<AccountManagementPage />} />
          <Route path="/account/trading" element={<TradingDeskPage />} />
          <Route path="/account/orders" element={<OrderQueryPage />} />
          <Route path="/strategies" element={<StrategiesPage />} />
          <Route path="/strategy-editor" element={<StrategyEditorPage />} />
          <Route path="/execution" element={<ExecutionPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/replay" element={<ReplayPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
