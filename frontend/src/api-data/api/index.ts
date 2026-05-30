import request from '@/common/utils/request'
import type {
  StockBaseInfo,
  KLineData,
  RealTimeQuote,
  SectorInfo,
  StockListItem,
  KLineQuery,
  BatchStockQuery,
  StockSyncRequest,
  KLineSyncRequest,
  StockSearchQuery,
} from '@/api-data/types'

// ========== 个股接口 ==========

export async function getStockBaseInfo(symbol: string): Promise<StockBaseInfo> {
  return request.get(`/api-data/stock/${symbol}/base`)
}

export async function syncStocks(data: StockSyncRequest): Promise<StockBaseInfo[]> {
  return request.post('/api-data/stock/sync', data)
}

export async function getStockList(market?: string): Promise<StockListItem[]> {
  return request.get('/api-data/stock/list', { params: { market } })
}

export async function searchStocks(params: StockSearchQuery): Promise<StockListItem[]> {
  return request.get('/api-data/stock/search', { params })
}

// ========== K线接口 ==========

export async function getKLine(
  symbol: string,
  params?: Partial<KLineQuery>
): Promise<KLineData[]> {
  return request.get(`/api-data/kline/${symbol}`, { params })
}

export async function syncKLine(symbol: string, data: KLineSyncRequest): Promise<KLineData[]> {
  return request.post(`/api-data/kline/${symbol}/sync`, data)
}

// ========== 实时行情接口 ==========

export async function getRealtimeQuote(symbol: string): Promise<RealTimeQuote> {
  return request.get(`/api-data/realtime/${symbol}`)
}

export async function getBatchRealtimeQuote(data: BatchStockQuery): Promise<RealTimeQuote[]> {
  return request.post('/api-data/realtime/batch', data)
}

// ========== 板块接口 ==========

export async function getSectorList(market?: string): Promise<SectorInfo[]> {
  return request.get('/api-data/sector', { params: { market } })
}

export async function getSectorStocks(sectorCode: string): Promise<StockListItem[]> {
  return request.get(`/api-data/sector/${sectorCode}/stocks`)
}