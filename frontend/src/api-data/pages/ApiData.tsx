import { useState, useEffect } from 'react'
import { Search, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react'
import { Link } from 'react-router-dom'
import { AppLayout } from '@/common/components'
import { formatNumber, formatPercent } from '@/common/utils'
import { getStockList, getBatchRealtimeQuote } from '@/api-data/api'
import type { StockListItem, RealTimeQuote } from '@/api-data/types'

export default function ApiData() {
  const [stocks, setStocks] = useState<StockListItem[]>([])
  const [quotes, setQuotes] = useState<Record<string, RealTimeQuote>>({})
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedMarket, setSelectedMarket] = useState<string | undefined>(undefined)

  useEffect(() => {
    loadStocks()
  }, [selectedMarket])

  async function loadStocks() {
    setLoading(true)
    try {
      const list = await getStockList(selectedMarket)
      setStocks(list)
      // 批量获取实时行情
      if (list.length > 0) {
        const symbols = list.slice(0, 20).map(s => s.symbol)
        const quotesData = await getBatchRealtimeQuote({ symbols })
        const quotesMap: Record<string, RealTimeQuote> = {}
        quotesData.forEach(q => { quotesMap[q.symbol] = q })
        setQuotes(quotesMap)
      }
    } catch (e) {
      console.error('Failed to load stocks:', e)
    } finally {
      setLoading(false)
    }
  }

  const filteredStocks = stocks.filter(s =>
    s.name.includes(search) || s.symbol.includes(search)
  )

  return (
    <AppLayout>
      <div className="space-y-4">
        {/* 搜索和筛选栏 */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant" />
            <input
              type="text"
              placeholder="搜索股票名称/代码..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-surface-container rounded-md text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedMarket(undefined)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${selectedMarket === undefined ? 'bg-primary text-on-primary' : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'}`}
            >
              全部
            </button>
            <button
              onClick={() => setSelectedMarket('A')}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${selectedMarket === 'A' ? 'bg-primary text-on-primary' : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'}`}
            >
              A股
            </button>
          </div>
          <button
            onClick={loadStocks}
            disabled={loading}
            className="p-2 rounded-md bg-surface-container text-on-surface-variant hover:bg-surface-container-high transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* 股票列表 */}
        <div className="bg-surface-container-high rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-on-surface-variant text-xs border-b border-outline-variant/20">
                <th className="text-left py-3 px-4 font-medium">代码</th>
                <th className="text-left py-3 px-4 font-medium">名称</th>
                <th className="text-left py-3 px-4 font-medium">市场</th>
                <th className="text-left py-3 px-4 font-medium">板块</th>
                <th className="text-right py-3 px-4 font-medium">最新价</th>
                <th className="text-right py-3 px-4 font-medium">涨跌幅</th>
                <th className="text-right py-3 px-4 font-medium">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/20">
              {filteredStocks.map(stock => {
                const quote = quotes[stock.symbol]
                return (
                  <tr key={stock.symbol} className="hover:bg-surface-container transition-colors">
                    <td className="py-3 px-4 font-mono-num">{stock.symbol}</td>
                    <td className="py-3 px-4 font-medium">{stock.name}</td>
                    <td className="py-3 px-4 text-on-surface-variant">{stock.market}</td>
                    <td className="py-3 px-4 text-on-surface-variant">{stock.sector || '-'}</td>
                    <td className="py-3 px-4 text-right font-mono-num">
                      {quote ? formatNumber(quote.last_price) : '-'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {quote ? (
                        <span className={`inline-flex items-center gap-1 font-mono-num ${quote.change_pct >= 0 ? 'text-up' : 'text-down'}`}>
                          {quote.change_pct >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                          {formatPercent(quote.change_pct)}
                        </span>
                      ) : '-'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/symbol-detail?symbol=${stock.symbol}`}
                        className="text-primary hover:text-primary/80 text-sm"
                      >
                        查看详情
                      </Link>
                    </td>
                  </tr>
                )
              })}
              {filteredStocks.length === 0 && !loading && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-on-surface-variant">
                    暂无数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  )
}