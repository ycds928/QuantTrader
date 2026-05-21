import { useState, useEffect } from 'react'
import { RefreshCw, TrendingUp, TrendingDown } from 'lucide-react'
import { AppLayout } from '@/common/components'
import { formatNumber, formatPercent } from '@/common/utils'
import { getSectorList, getBatchRealtimeQuote, getStockList } from '@/api-data/api'
import type { SectorInfo, RealTimeQuote } from '@/api-data/types'

export default function Dashboard() {
  const [sectors, setSectors] = useState<SectorInfo[]>([])
  const [hotStocks, setHotStocks] = useState<Array<RealTimeQuote & { name: string }>>([])
  const [marketStats, setMarketStats] = useState({ upCount: 0, downCount: 0, volume: 0 })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadDashboardData()
  }, [])

  async function loadDashboardData() {
    setLoading(true)
    try {
      const [sectorList, stockList] = await Promise.all([
        getSectorList(),
        getStockList(),
      ])
      setSectors(sectorList)

      // 获取热门股票行情（取前10只）
      const symbols = stockList.slice(0, 10).map(s => s.symbol)
      const quotes = await getBatchRealtimeQuote({ symbols })
      const quotesMap: Record<string, string> = {}
      stockList.forEach(s => { quotesMap[s.symbol] = s.name })

      const hotStocksWithName = quotes.map(q => ({
        ...q,
        name: quotesMap[q.symbol] || q.symbol,
      })) as Array<RealTimeQuote & { name: string }>

      // 按涨跌幅排序
      hotStocksWithName.sort((a, b) => b.change_pct - a.change_pct)
      setHotStocks(hotStocksWithName)

      // 计算市场统计
      const upCount = quotes.filter(q => q.change_pct > 0).length
      const downCount = quotes.filter(q => q.change_pct < 0).length
      const totalVolume = quotes.reduce((acc, q) => acc + q.volume, 0)
      setMarketStats({
        upCount,
        downCount,
        volume: totalVolume,
      })
    } catch (e) {
      console.error('Failed to load dashboard:', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppLayout>
      <div className="space-y-4">
        {/* 顶部统计卡片 */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-surface-container-high rounded-lg p-4">
            <div className="text-xs text-on-surface-variant mb-1">上涨家数</div>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold text-up">{marketStats.upCount}</span>
              <TrendingUp className="w-4 h-4 text-up" />
            </div>
          </div>
          <div className="bg-surface-container-high rounded-lg p-4">
            <div className="text-xs text-on-surface-variant mb-1">下跌家数</div>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold text-down">{marketStats.downCount}</span>
              <TrendingDown className="w-4 h-4 text-down" />
            </div>
          </div>
          <div className="bg-surface-container-high rounded-lg p-4">
            <div className="text-xs text-on-surface-variant mb-1">总成交量</div>
            <div className="text-xl font-bold font-mono-num">{formatNumber(marketStats.volume)}</div>
          </div>
          <div className="bg-surface-container-high rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-on-surface-variant mb-1">市场情绪</div>
                <div className="text-xl font-bold">
                  {marketStats.upCount > marketStats.downCount ? (
                    <span className="text-up">偏多</span>
                  ) : marketStats.upCount < marketStats.downCount ? (
                    <span className="text-down">偏空</span>
                  ) : (
                    <span>中性</span>
                  )}
                </div>
              </div>
              <button
                onClick={loadDashboardData}
                disabled={loading}
                className="p-2 rounded-md hover:bg-surface-container-high transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* 中部：板块和热门股票 */}
        <div className="grid grid-cols-3 gap-4">
          {/* 板块列表 */}
          <div className="col-span-1 bg-surface-container-high rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3">板块列表</h3>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {sectors.map(sector => (
                <div
                  key={sector.sector_code}
                  className="flex items-center justify-between p-2 rounded-md bg-surface-container hover:bg-surface-container-high transition-colors cursor-pointer"
                >
                  <div>
                    <div className="text-sm font-medium">{sector.sector_name}</div>
                    <div className="text-xs text-on-surface-variant">{sector.stock_count}只股票</div>
                  </div>
                </div>
              ))}
              {sectors.length === 0 && (
                <div className="text-sm text-on-surface-variant text-center py-4">暂无数据</div>
              )}
            </div>
          </div>

          {/* 热门股票 */}
          <div className="col-span-2 bg-surface-container-high rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3">热门股票</h3>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {hotStocks.map(stock => (
                <div
                  key={stock.symbol}
                  className="flex items-center justify-between p-2 rounded-md bg-surface-container hover:bg-surface-container-high transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div>
                      <div className="text-sm font-medium">{stock.name}</div>
                      <div className="text-xs text-on-surface-variant font-mono-num">{stock.symbol}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-mono-num font-medium">{formatNumber(stock.last_price)}</div>
                    <div className={`text-xs font-mono-num ${stock.change_pct >= 0 ? 'text-up' : 'text-down'}`}>
                      {stock.change_pct >= 0 ? '+' : ''}{formatPercent(stock.change_pct)}
                    </div>
                  </div>
                </div>
              ))}
              {hotStocks.length === 0 && (
                <div className="text-sm text-on-surface-variant text-center py-4">暂无数据</div>
              )}
            </div>
          </div>
        </div>

        {/* 涨幅/跌幅榜 */}
        <div className="grid grid-cols-2 gap-4">
          {/* 涨幅榜 */}
          <div className="bg-surface-container-high rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3 text-up">涨幅榜</h3>
            <div className="space-y-2">
              {hotStocks.filter(s => s.change_pct > 0).slice(0, 5).map(stock => (
                <div key={stock.symbol} className="flex items-center justify-between p-2 rounded-md bg-surface-container">
                  <div>
                    <span className="text-sm font-medium">{stock.name}</span>
                    <span className="text-xs text-on-surface-variant ml-2 font-mono-num">{stock.symbol}</span>
                  </div>
                  <span className="text-sm font-mono-num text-up">+{formatPercent(stock.change_pct)}</span>
                </div>
              ))}
              {hotStocks.filter(s => s.change_pct > 0).length === 0 && (
                <div className="text-sm text-on-surface-variant text-center py-2">暂无数据</div>
              )}
            </div>
          </div>

          {/* 跌幅榜 */}
          <div className="bg-surface-container-high rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3 text-down">跌幅榜</h3>
            <div className="space-y-2">
              {hotStocks.filter(s => s.change_pct < 0).slice(0, 5).map(stock => (
                <div key={stock.symbol} className="flex items-center justify-between p-2 rounded-md bg-surface-container">
                  <div>
                    <span className="text-sm font-medium">{stock.name}</span>
                    <span className="text-xs text-on-surface-variant ml-2 font-mono-num">{stock.symbol}</span>
                  </div>
                  <span className="text-sm font-mono-num text-down">{formatPercent(stock.change_pct)}</span>
                </div>
              ))}
              {hotStocks.filter(s => s.change_pct < 0).length === 0 && (
                <div className="text-sm text-on-surface-variant text-center py-2">暂无数据</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}