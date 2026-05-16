import { AppLayout } from '@/common/components'
import { Brain } from 'lucide-react'

export default function Strategies() {
  return (
    <AppLayout>
      <div className="flex flex-col items-center justify-center h-full text-on-surface-variant">
        <Brain className="w-12 h-12 mb-4 opacity-30" />
        <h2 className="text-lg font-semibold mb-2 text-on-surface">策略管理</h2>
        <p className="text-sm">该模块正在开发中</p>
      </div>
    </AppLayout>
  )
}
