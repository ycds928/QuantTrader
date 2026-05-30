/** 个股基础信息 */
export interface StockBaseInfo {
  id: number
  symbol: string
  name: string
  market: string
  sector: string | null
  IPO_date: string | null
  total_shares: number | null
  float_shares: number | null
  status: string
  created_at: string
  updated_at: string
}

/** K线数据 */
export interface KLineData {
  id: number
  symbol: string
  timeframe: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  turnover: number | null
}

/** 实时行情 */
export interface RealTimeQuote {
  id: number
  symbol: string
  name: string
  last_price: number
  change: number
  change_pct: number
  open: number
  high: number
  low: number
  volume: number
  turnover: number | null
  amplitude: number | null
  market_cap: number | null
  float_market_cap: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  timestamp: string
}

/** 板块信息 */
export interface SectorInfo {
  id: number
  sector_code: string
  sector_name: string
  market: string
  stock_count: number
  description: string | null
}

/** 股票列表项（简化） */
export interface StockListItem {
  symbol: string
  name: string
  market: string
  sector: string | null
}

/** 股票搜索查询 */
export interface StockSearchQuery {
  keyword: string
  market?: string
  limit?: number
}

/** K线查询参数 */
export interface KLineQuery {
  symbol: string
  timeframe?: string  // 时间周期: 1m/5m/15m/30m/1h/1d/1w
  start_date?: string
  end_date?: string
  limit?: number
}

/** 批量股票查询 */
export interface BatchStockQuery {
  symbols: string[]
}

/** 股票同步请求 */
export interface StockSyncRequest {
  symbols?: string[]
}

/** K线同步请求 */
export interface KLineSyncRequest {
  timeframe?: string
  start_date?: string
  end_date?: string
}

/** 板块成分股查询 */
export interface SectorStocksQuery {
  sector_code: string
}