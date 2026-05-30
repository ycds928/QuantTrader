import { useState, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { AppLayout } from '@/common/components'
import { formatNumber, formatPercent } from '@/common/utils'
import {
  getStockBaseInfo,
  getKLine,
  getRealtimeQuote,
  getSectorStocks,
} from '@/api-data/api'
import type { StockBaseInfo, KLineData, RealTimeQuote, StockListItem } from '@/api-data/types'

// 支持的K线周期
const TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '1d', '1w']
// 周期显示名称映射
const TIMEFRAME_LABELS: Record<string, string> = {
  '1m': '1分',
  '5m': '5分',
  '15m': '15分',
  '30m': '30分',
  '1h': '1时',
  '1d': '日',
  '1w': '周',
}

export default function SymbolDetail() {
  const [searchParams] = useSearchParams()
  const symbol = searchParams.get('symbol') || '000001'

  const [stockInfo, setStockInfo] = useState<StockBaseInfo | null>(null)
  const [quote, setQuote] = useState<RealTimeQuote | null>(null)
  const [klines, setKlines] = useState<KLineData[]>([])
  const [relatedStocks, setRelatedStocks] = useState<StockListItem[]>([])
  const [timeframe, setTimeframe] = useState('1d')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [symbol, timeframe])

  async function loadData() {
    setLoading(true)
    try {
      const [info, quoteData, klineData] = await Promise.all([
        getStockBaseInfo(symbol),
        getRealtimeQuote(symbol),
        getKLine(symbol, { timeframe, limit: 100 }),
      ])
      setStockInfo(info)
      setQuote(quoteData)
      setKlines(klineData.reverse())

      // 获取同板块股票
      if (info.sector) {
        try {
          // 简单通过板块名查找相关股票
          const stocks = await getSectorStocks(info.sector)
          setRelatedStocks(stocks.filter(s => s.symbol !== symbol).slice(0, 5))
        } catch {}
      }
    } catch (e) {
      console.error('Failed to load data:', e)
    } finally {
      setLoading(false)
    }
  }

  // 计算简单技术指标
  function calcMA(data: KLineData[], period: number): number | null {
    if (data.length < period) return null
    const sum = data.slice(-period).reduce((acc, k) => acc + k.close, 0)
    return sum / period
  }

  const ma5 = calcMA(klines, 5)
  const ma10 = calcMA(klines, 10)
  const ma20 = calcMA(klines, 20)

  // 简单的K线柱状图渲染
  function renderKLineChart() {
    if (klines.length === 0) return null

    const maxHigh = Math.max(...klines.map(k => k.high))
    const minLow = Math.min(...klines.map(k => k.low))
    const range = maxHigh - minLow || 1

    return (
      <div className="flex items-end h-full gap-[2px]">
        {klines.map((k, i) => {
          const bodyTop = ((maxHigh - Math.max(k.open, k.close)) / range) * 100
          const bodyBottom = ((maxHigh - Math.min(k.open, k.close)) / range) * 100
          const isUp = k.close >= k.open
          return (
            <div
              key={i}
              className="flex-1 relative"
              style={{ height: '100%' }}
            >
              <div
                className="absolute w-full bg-outline-variant/30"
                style={{
                  bottom: `${((k.low - minLow) / range) * 100}%`,
                  height: `${((k.high - k.low) / range) * 100}%`,
                }}
              />
              <div
                className="absolute w-full"
                style={{
                  bottom: `${bodyBottom}%`,
                  height: `${bodyBottom - bodyTop}%`,
                  backgroundColor: isUp ? 'rgb(239, 68, 68)' : 'rgb(34, 197, 94)',
                }}
              />
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <AppLayout>
      <div className="space-y-4">
        {/* 顶部导航 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              to="/api-data"
              className="p-2 rounded-md hover:bg-surface-container-high transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <h1 className="text-lg font-bold">{stockInfo?.name || symbol}</h1>
              <span className="text-sm text-on-surface-variant font-mono-num">{symbol}</span>
            </div>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 rounded-md bg-surface-container text-on-surface-variant hover:bg-surface-container-high transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* 行情概览 */}
        {quote && (
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-surface-container-high rounded-lg p-4">
              <div className="text-xs text-on-surface-variant mb-1">最新价</div>
              <div className="text-xl font-bold font-mono-num">{formatNumber(quote.last_price)}</div>
              <div className={`text-sm font-mono-num ${quote.change_pct >= 0 ? 'text-up' : 'text-down'}`}>
                {quote.change >= 0 ? '+' : ''}{formatNumber(quote.change)} ({formatPercent(quote.change_pct)})
              </div>
            </div>
            <div className="bg-surface-container-high rounded-lg p-4">
              <div className="text-xs text-on-surface-variant mb-1">开盘价</div>
              <div className="text-xl font-bold font-mono-num">{formatNumber(quote.open)}</div>
            </div>
            <div className="bg-surface-container-high rounded-lg p-4">
              <div className="text-xs text-on-surface-variant mb-1">最高价</div>
              <div className="text-xl font-bold font-mono-num text-up">{formatNumber(quote.high)}</div>
            </div>
            <div className="bg-surface-container-high rounded-lg p-4">
              <div className="text-xs text-on-surface-variant mb-1">最低价</div>
              <div className="text-xl font-bold font-mono-num text-down">{formatNumber(quote.low)}</div>
            </div>
          </div>
        )}

        {/* K线图表 */}
        <div className="bg-surface-container-high rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold">K线走势</h3>
            <div className="flex items-center gap-1">
              {TIMEFRAMES.map(tf => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1 text-xs rounded-md transition-colors ${timeframe === tf ? 'bg-primary text-on-primary' : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'}`}
                >
                  {TIMEFRAME_LABELS[tf] || tf}
                </button>
              ))}
            </div>
          </div>
          <div className="h-64">
            {renderKLineChart()}
          </div>
          {/* MA指标 */}
          <div className="flex items-center gap-4 mt-3 text-xs text-on-surface-variant">
            <span>MA5: {ma5 ? formatNumber(ma5) : '-'}</span>
            <span>MA10: {ma10 ? formatNumber(ma10) : '-'}</span>
            <span>MA20: {ma20 ? formatNumber(ma20) : '-'}</span>
          </div>
        </div>

        {/* 股票信息和相关股票 */}
        <div className="grid grid-cols-2 gap-4">
          {/* 基本信息 */}
          <div className="bg-surface-container-high rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3">基本信息</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-on-surface-variant">所属行业</dt>
              <dd>{stockInfo?.sector || '-'}</dd>
              <dt className="text-on-surface-variant">上市日期</dt>
              <dd>{stockInfo?.IPO_date || '-'}</dd>
              <dt className="text-on-surface-variant">总股本</dt>
              <dd>{stockInfo?.total_shares ? formatNumber(stockInfo.total_shares) + '万股' : '-'}</dd>
              <dt className="text-on-surface-variant">流通股本</dt>
              <dd>{stockInfo?.float_shares ? formatNumber(stockInfo.float_shares) + '万股' : '-'}</dd>
              <dt className="text-on-surface-variant">市盈率</dt>
              <dd>{quote?.pe_ratio ? formatNumber(quote.pe_ratio) : '-'}</dd>
              <dt className="text-on-surface-variant">市净率</dt>
              <dd>{quote?.pb_ratio ? formatNumber(quote.pb_ratio) : '-'}</dd>
            </dl>
          </div>

          {/* 相关股票 */}
          <div className="bg-surface-container-high rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3">同板块股票</h3>
            {relatedStocks.length > 0 ? (
              <div className="space-y-2">
                {relatedStocks.map(s => (
                  <Link
                    key={s.symbol}
                    to={`/symbol-detail?symbol=${s.symbol}`}
                    className="flex items-center justify-between p-2 rounded-md bg-surface-container hover:bg-surface-container-high transition-colors"
                  >
                    <div>
                      <span className="font-medium text-sm">{s.name}</span>
                      <span className="text-xs text-on-surface-variant ml-2 font-mono-num">{s.symbol}</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-sm text-on-surface-variant">暂无数据</div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}