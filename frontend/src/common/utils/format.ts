/** 格式化数字为千分位 */
export function formatNumber(value: number, decimals = 2): string {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/** 格式化百分比 */
export function formatPercent(value: number, decimals = 2): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(decimals)}%`
}

/** 格式化价格（数字字体） */
export function formatPrice(value: number, decimals = 2): string {
  return formatNumber(value, decimals)
}

/** 格式化盈亏值 */
export function formatPnL(value: number, decimals = 2): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${formatNumber(value, decimals)}`
}

/** 格式化日期时间 */
export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/** 格式化日期 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}
