import { AppLayout } from '@/common/components'
import { MonitorPlay } from 'lucide-react'

export default function Execution() {
  return (
    <AppLayout>
      <div className="flex flex-col items-center justify-center h-full text-on-surface-variant">
        <MonitorPlay className="w-12 h-12 mb-4 opacity-30" />
        <h2 className="text-lg font-semibold mb-2 text-on-surface">执行监控</h2>
        <p className="text-sm">该模块正在开发中</p>
      </div>
    </AppLayout>
  )
}
