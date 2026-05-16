import { AppLayout } from '@/common/components'

export default function Dashboard() {
  return (
    <AppLayout>
      <div className="space-y-6">
        {/* 顶部指标卡片行 */}
        <div className="grid grid-cols-4 gap-4">
          <MetricCard label="总资产" value="¥1,258,432.50" icon="wallet" />
          <MetricCard
            label="当日盈亏"
            value="+¥12,350.80"
            subvalue="+0.99%"
            trend="up"
          />
          <MetricCard label="运行策略" value="3" icon="brain" />
          <MetricCard label="活跃告警" value="2" icon="alert-triangle" />
        </div>

        {/* 中部图表区 */}
        <div className="grid grid-cols-3 gap-4">
          {/* 资产曲线 */}
          <div className="col-span-2 bg-surface-container-high shadow-card rounded-lg p-5">
            <h3 className="text-sm font-semibold mb-4">资产曲线</h3>
            <div className="h-64 flex items-center justify-center text-on-surface-variant text-sm">
              资产曲线图表（ECharts）
            </div>
          </div>

          {/* 持仓分布 */}
          <div className="bg-surface-container-high shadow-card rounded-lg p-5">
            <h3 className="text-sm font-semibold mb-4">持仓分布</h3>
            <div className="h-64 flex items-center justify-center text-on-surface-variant text-sm">
              持仓饼图（ECharts）
            </div>
          </div>
        </div>

        {/* 底部区域 */}
        <div className="grid grid-cols-2 gap-4">
          {/* 最近交易 */}
          <div className="bg-surface-container-high shadow-card rounded-lg p-5">
            <h3 className="text-sm font-semibold mb-4">最近交易</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-on-surface-variant text-xs">
                  <th className="text-left py-2 font-medium">交易对</th>
                  <th className="text-left py-2 font-medium">方向</th>
                  <th className="text-right py-2 font-medium">价格</th>
                  <th className="text-right py-2 font-medium">数量</th>
                  <th className="text-right py-2 font-medium">盈亏</th>
                  <th className="text-right py-2 font-medium">时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/20">
                {[
                  { symbol: 'BTC/USDT', side: '买入', price: '97,245.30', qty: '0.12', pnl: '+¥1,234.50', pnlUp: true, time: '14:32:05' },
                  { symbol: 'ETH/USDT', side: '卖出', price: '3,856.20', qty: '2.50', pnl: '-¥320.00', pnlUp: false, time: '13:18:42' },
                  { symbol: 'SOL/USDT', side: '买入', price: '185.60', qty: '50', pnl: '+¥890.00', pnlUp: true, time: '11:05:28' },
                  { symbol: 'BTC/USDT', side: '卖出', price: '97,102.80', qty: '0.05', pnl: '-¥56.75', pnlUp: false, time: '10:22:15' },
                  { symbol: 'ETH/USDT', side: '买入', price: '3,812.40', qty: '5.00', pnl: '+¥2,190.00', pnlUp: true, time: '09:45:33' },
                ].map((row, i) => (
                  <tr key={i} className="hover:bg-surface-container-highest transition-colors">
                    <td className="py-2 font-medium">{row.symbol}</td>
                    <td className={`py-2 ${row.side === '买入' ? 'text-up' : 'text-down'}`}>{row.side}</td>
                    <td className="py-2 text-right font-mono-num">{row.price}</td>
                    <td className="py-2 text-right font-mono-num">{row.qty}</td>
                    <td className={`py-2 text-right font-mono-num ${row.pnlUp ? 'text-up' : 'text-down'}`}>{row.pnl}</td>
                    <td className="py-2 text-right text-on-surface-variant">{row.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 告警列表 */}
          <div className="bg-surface-container-high shadow-card rounded-lg p-5">
            <h3 className="text-sm font-semibold mb-4">活跃告警</h3>
            <div className="space-y-3">
              {[
                { level: 'critical', strategy: '网格交易-BTC', message: '单笔亏损超过止损阈值 -2.5%', time: '14:28:10' },
                { level: 'warning', strategy: '趋势追踪-ETH', message: '持仓占比超过 80% 上限', time: '13:55:32' },
                { level: 'critical', strategy: '均线交叉-SOL', message: '连续亏损达到 5 次', time: '12:10:05' },
              ].map((alert, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-surface-container rounded-lg">
                  <span
                    className={`shrink-0 px-2 py-0.5 text-xs font-medium rounded-full ${
                      alert.level === 'critical'
                        ? 'bg-error/20 text-error'
                        : 'bg-warning/20 text-warning'
                    }`}
                  >
                    {alert.level === 'critical' ? '严重' : '警告'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{alert.strategy}</span>
                      <span className="text-xs text-on-surface-variant">{alert.time}</span>
                    </div>
                    <p className="text-xs text-on-surface-variant mt-0.5">{alert.message}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

function MetricCard({
  label,
  value,
  subvalue,
  trend,
}: {
  label: string
  value: string
  subvalue?: string
  trend?: 'up' | 'down'
  icon?: string
}) {
  return (
    <div className="bg-surface-container-high shadow-card rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-on-surface-variant">{label}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-xl font-bold font-mono-num">{value}</span>
        {subvalue && (
          <span className={`text-sm font-mono-num ${trend === 'up' ? 'text-up' : 'text-down'}`}>
            {subvalue}
          </span>
        )}
      </div>
    </div>
  )
}
