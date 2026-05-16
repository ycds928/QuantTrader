import { Activity } from 'lucide-react'
import { AppLayout } from '@/common/components'

export default function ApiData() {
  return (
    <AppLayout>
      <div className="flex flex-col items-center justify-center h-full text-on-surface-variant">
        <Activity className="w-12 h-12 mb-4 opacity-30" />
        <h2 className="text-lg font-semibold mb-2 text-on-surface">行情数据</h2>
        <p className="text-sm">该模块正在开发中</p>
      </div>
    </AppLayout>
  )
}
