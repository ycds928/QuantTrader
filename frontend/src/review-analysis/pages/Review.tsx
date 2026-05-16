import { AppLayout } from '@/common/components'
import { ChartBar } from 'lucide-react'

export default function Review() {
  return (
    <AppLayout>
      <div className="flex flex-col items-center justify-center h-full text-on-surface-variant">
        <ChartBar className="w-12 h-12 mb-4 opacity-30" />
        <h2 className="text-lg font-semibold mb-2 text-on-surface">复盘分析</h2>
        <p className="text-sm">该模块正在开发中</p>
      </div>
    </AppLayout>
  )
}
