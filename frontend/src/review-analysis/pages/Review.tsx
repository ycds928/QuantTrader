import { AppLayout } from '@/common/components'
import request from '@/common/utils/request'
import ReactECharts from 'echarts-for-react'
import { AlertTriangle, BarChart3, CheckCircle2, Loader2, RefreshCcw, Search, Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

type ApiResponse<T> = { success: boolean; data: T; message: string }

type ReviewAccount = {
  id: number
  account_code: string
  account_name: string
  account_type: 'live' | 'paper' | 'backtest'
  broker_name: string | null
  status: string
  is_default: boolean
}

type ReviewSession = {
  id: number
  session_code: string
  title: string
  account_id: number
  account_name: string
  account_type: 'live' | 'paper' | 'backtest'
  source: string
  strategy_id: string | null
  version_id: string | null
  start_date: string
  end_date: string
  status: string
  summary: Record<string, unknown>
  created_at: string
}

type MetricItem = {
  key: string
  value: string | null
  text: string | null
  unit: string | null
  group: string | null
}

type EquityPoint = {
  date: string
  time: string
  equity: string
  total_asset: string
  cash_balance: string
  market_value: string
  cumulative_return: string
}

type DrawdownPoint = {
  date: string
  time: string
  equity: string
  peak_equity: string
  drawdown: string
  drawdown_amount: string
}

type ReviewSuggestion = {
  id: number
  type: string
  severity: 'low' | 'medium' | 'high'
  title: string
  content: string
  evidence: Record<string, unknown>
  status: string
}

type ReviewTrade = {
  id: number
  trade_id: string | null
  symbol: string
  name: string
  side: string
  price: string
  quantity: number
  amount: string
  pnl: string | null
  pnl_ratio: string | null
  holding_period_minutes: number | null
  traded_at: string
}

type ReviewReport = {
  session: ReviewSession
  metrics: Record<string, MetricItem>
  equity_curve: EquityPoint[]
  drawdown_curve: DrawdownPoint[]
  suggestions: ReviewSuggestion[]
  recent_trades: ReviewTrade[]
}

const apiTimeout = 240000
const inputClass =
  'h-10 w-full rounded-md border border-outline bg-surface-container px-3 text-sm text-on-surface outline-none transition-colors placeholder:text-on-surface-variant focus:border-primary'

export default function Review() {
  const [accounts, setAccounts] = useState<ReviewAccount[]>([])
  const [sessions, setSessions] = useState<ReviewSession[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)
  const [report, setReport] = useState<ReviewReport | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState(() => {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 30)
    return {
      account_id: '',
      start_date: start.toISOString().slice(0, 10),
      end_date: end.toISOString().slice(0, 10),
      title: '',
      strategy_id: '',
      version_id: '',
      benchmark_symbol: '000300.SH',
      run_id: '',
    }
  })

  const busyText = useMemo(
    () =>
      ({
        accounts: '加载账户',
        sessions: '加载会话',
        report: '加载报告',
        generate: '生成复盘',
        delete: '删除复盘',
      })[busy || ''] || '',
    [busy]
  )

  const keyMetrics = useMemo(() => {
    if (!report) return []
    return [
      ['total_return', '累计收益'],
      ['realized_pnl', '已实现盈亏'],
      ['max_drawdown', '最大回撤'],
      ['win_rate', '胜率'],
      ['trade_count', '成交笔数'],
      ['fee_ratio', '成本占比'],
    ].map(([key, label]) => ({ key, label, metric: report.metrics[key] }))
  }, [report])

  useEffect(() => {
    void bootstrap()
  }, [])

  async function callApi<T>(label: string, work: () => Promise<ApiResponse<T>>) {
    setBusy(label)
    setError('')
    setMessage('')
    try {
      const response = await work()
      setMessage(response.message)
      return response.data
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(detail?.message || err?.message || '请求失败')
      return null
    } finally {
      setBusy(null)
    }
  }

  async function bootstrap() {
    const accountData = await loadAccounts()
    const sessionData = await loadSessions()
    if (accountData?.length) {
      const defaultAccount = accountData.find((item) => item.is_default) || accountData[0]
      setForm((prev) => ({ ...prev, account_id: String(defaultAccount.id) }))
    }
    if (sessionData?.length) {
      setSelectedSessionId(sessionData[0].id)
      await loadReport(sessionData[0].id)
    }
  }

  async function loadAccounts() {
    const data = await callApi<ReviewAccount[]>('accounts', () =>
      request.get('/review/accounts', { timeout: apiTimeout }) as Promise<ApiResponse<ReviewAccount[]>>
    )
    if (data) setAccounts(data)
    return data
  }

  async function loadSessions() {
    const data = await callApi<ReviewSession[]>('sessions', () =>
      request.get('/review/sessions', { timeout: apiTimeout }) as Promise<ApiResponse<ReviewSession[]>>
    )
    if (data) setSessions(data)
    return data
  }

  async function loadReport(sessionId = selectedSessionId) {
    if (!sessionId) return
    const data = await callApi<ReviewReport>('report', () =>
      request.get('/review/report', {
        params: { session_id: sessionId },
        timeout: apiTimeout,
      }) as Promise<ApiResponse<ReviewReport>>
    )
    if (data) {
      setReport(data)
      setSelectedSessionId(data.session.id)
    }
  }

  async function generateReview(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = {
      account_id: Number(form.account_id),
      start_date: form.start_date || undefined,
      end_date: form.end_date || undefined,
      title: form.title.trim() || undefined,
      strategy_id: form.strategy_id.trim() || undefined,
      version_id: form.version_id.trim() || undefined,
      benchmark_symbol: form.benchmark_symbol.trim() || undefined,
      run_id: form.run_id.trim() || undefined,
    }
    const data = await callApi<ReviewReport>('generate', () =>
      request.post('/review/sessions/generate', payload, { timeout: apiTimeout }) as Promise<ApiResponse<ReviewReport>>
    )
    if (data) {
      setReport(data)
      setSelectedSessionId(data.session.id)
      await loadSessions()
    }
  }

  async function deleteSession() {
    if (!selectedSessionId) return
    const confirmed = window.confirm('确认删除当前复盘会话及其指标、曲线、建议吗？')
    if (!confirmed) return
    const data = await callApi<{ deleted: boolean }>('delete', () =>
      request.delete(`/review/sessions/${selectedSessionId}`, { timeout: apiTimeout }) as Promise<ApiResponse<{ deleted: boolean }>>
    )
    if (data) {
      setReport(null)
      setSelectedSessionId(null)
      const nextSessions = await loadSessions()
      if (nextSessions?.length) {
        setSelectedSessionId(nextSessions[0].id)
        await loadReport(nextSessions[0].id)
      }
    }
  }

  const chartOption = useMemo(() => buildChartOption(report?.equity_curve || [], report?.drawdown_curve || []), [report])

  return (
    <AppLayout>
      <div className="space-y-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-on-surface">复盘与策略优化</h1>
            <p className="mt-1 text-sm text-on-surface-variant">从实盘、模拟盘、回测账户的成交和资金快照生成复盘指标、曲线和优化建议。</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ActionButton label="刷新会话" icon={<RefreshCcw className="size-4" />} onClick={() => void loadSessions()} />
            <ActionButton label="查看报告" icon={<Search className="size-4" />} onClick={() => void loadReport()} disabled={!selectedSessionId} />
          </div>
        </div>

        {(message || error || busy) && <Notice busy={busyText} message={message} error={error} />}

        <div className="grid gap-4 xl:grid-cols-[380px_1fr]">
          <div className="space-y-4">
            <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-semibold">生成复盘</h2>
                <span className="rounded-sm bg-primary/10 px-2 py-1 text-xs text-primary">模块5</span>
              </div>
              <form className="space-y-3" onSubmit={generateReview}>
                <Field label="复盘账户">
                  <select
                    value={form.account_id}
                    onChange={(event) => setForm({ ...form, account_id: event.target.value })}
                    className={inputClass}
                    required
                  >
                    <option value="">请选择账户</option>
                    {accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.account_name} / {accountTypeLabel(account.account_type)} / {account.account_code}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="开始日期">
                    <input type="date" value={form.start_date} onChange={(event) => setForm({ ...form, start_date: event.target.value })} className={inputClass} />
                  </Field>
                  <Field label="结束日期">
                    <input type="date" value={form.end_date} onChange={(event) => setForm({ ...form, end_date: event.target.value })} className={inputClass} />
                  </Field>
                </div>
                <Field label="复盘标题">
                  <input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} className={inputClass} placeholder="留空自动生成" />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="策略 ID">
                    <input value={form.strategy_id} onChange={(event) => setForm({ ...form, strategy_id: event.target.value })} className={inputClass} placeholder="可选" />
                  </Field>
                  <Field label="版本 ID">
                    <input value={form.version_id} onChange={(event) => setForm({ ...form, version_id: event.target.value })} className={inputClass} placeholder="可选" />
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="基准代码">
                    <input value={form.benchmark_symbol} onChange={(event) => setForm({ ...form, benchmark_symbol: event.target.value })} className={inputClass} placeholder="000300.SH" />
                  </Field>
                  <Field label="回测批次">
                    <input value={form.run_id} onChange={(event) => setForm({ ...form, run_id: event.target.value })} className={inputClass} placeholder="回测账户可填" />
                  </Field>
                </div>
                <button type="submit" disabled={Boolean(busy) || !form.account_id} className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-on-primary disabled:cursor-not-allowed disabled:opacity-60">
                  {busy === 'generate' ? <Loader2 className="size-4 animate-spin" /> : <BarChart3 className="size-4" />}
                  生成复盘
                </button>
              </form>
            </section>

            <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-semibold">复盘会话</h2>
                <ActionButton label="删除" icon={<Trash2 className="size-4" />} onClick={deleteSession} disabled={!selectedSessionId} />
              </div>
              <div className="space-y-2">
                {sessions.length ? (
                  sessions.map((session) => (
                    <button
                      key={session.id}
                      type="button"
                      onClick={() => void loadReport(session.id)}
                      className={`w-full rounded-md border px-3 py-2 text-left text-sm transition-colors ${selectedSessionId === session.id ? 'border-primary bg-primary/10' : 'border-outline bg-surface-container hover:bg-surface-container-highest'}`}
                    >
                      <div className="truncate font-medium text-on-surface">{session.title}</div>
                      <div className="mt-1 flex items-center justify-between gap-2 text-xs text-on-surface-variant">
                        <span>{accountTypeLabel(session.account_type)} / {session.start_date} 至 {session.end_date}</span>
                        <span className="font-mono-num">#{session.id}</span>
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="flex h-40 items-center justify-center rounded-md border border-outline-variant text-sm text-on-surface-variant">暂无复盘会话</div>
                )}
              </div>
            </section>
          </div>

          <div className="space-y-4">
            {report ? (
              <>
                <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
                  <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <h2 className="text-sm font-semibold">{report.session.title}</h2>
                      <p className="mt-1 text-xs text-on-surface-variant">
                        {report.session.account_name || '账户'} / {accountTypeLabel(report.session.account_type)} / {report.session.start_date} 至 {report.session.end_date}
                      </p>
                    </div>
                    <span className="rounded-sm bg-success/10 px-2 py-1 text-xs text-success">{report.session.status === 'done' ? '已生成' : report.session.status}</span>
                  </div>
                  <div className="grid gap-3 md:grid-cols-3 2xl:grid-cols-6">
                    {keyMetrics.map((item) => (
                      <MetricBlock key={item.key} label={item.label} metric={item.metric} tone={metricTone(item.key, item.metric?.value)} />
                    ))}
                  </div>
                </section>

                <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-sm font-semibold">净值与回撤</h2>
                    <span className="text-xs text-on-surface-variant">{report.equity_curve.length} 个曲线点</span>
                  </div>
                  <div className="h-80">
                    <ReactECharts option={chartOption} style={{ height: '100%', width: '100%' }} notMerge lazyUpdate />
                  </div>
                </section>

                <div className="grid gap-4 2xl:grid-cols-[1fr_420px]">
                  <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
                    <div className="mb-4 flex items-center justify-between">
                      <h2 className="text-sm font-semibold">复盘交易明细</h2>
                      <span className="text-xs text-on-surface-variant">最近 {report.recent_trades.length} 笔</span>
                    </div>
                    <DataTable
                      empty="暂无复盘交易"
                      headers={['时间', '代码', '方向', '价格', '数量', '金额', '盈亏', '持仓']}
                      rows={report.recent_trades.map((row) => [
                        row.traded_at || row.trade_id || '-',
                        row.symbol,
                        <SideText side={row.side} />,
                        money(row.price),
                        numberText(row.quantity),
                        money(row.amount),
                        <span className={pnlClass(row.pnl)}>{money(row.pnl)}</span>,
                        holdingText(row.holding_period_minutes),
                      ])}
                    />
                  </section>

                  <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
                    <div className="mb-4 flex items-center justify-between">
                      <h2 className="text-sm font-semibold">策略优化建议</h2>
                      <Sparkles className="size-4 text-primary" />
                    </div>
                    <div className="space-y-3">
                      {report.suggestions.length ? (
                        report.suggestions.map((item) => <SuggestionItem key={item.id} item={item} />)
                      ) : (
                        <div className="flex h-48 items-center justify-center rounded-md border border-outline-variant text-sm text-on-surface-variant">暂无优化建议</div>
                      )}
                    </div>
                  </section>
                </div>
              </>
            ) : (
              <section className="flex min-h-[520px] items-center justify-center rounded-lg bg-surface-container-high p-6 text-center text-on-surface-variant shadow-card">
                <div>
                  <BarChart3 className="mx-auto mb-4 size-12 opacity-40" />
                  <h2 className="text-base font-semibold text-on-surface">还没有可展示的复盘报告</h2>
                  <p className="mt-2 text-sm">选择账户和日期范围后生成一轮复盘，系统会写入指标、曲线、交易明细和优化建议。</p>
                </div>
              </section>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-on-surface-variant">{label}</span>
      {children}
    </label>
  )
}

function Notice({ busy, message, error }: { busy: string; message: string; error: string }) {
  return (
    <div className="rounded-md border border-outline bg-surface-container px-4 py-3 text-sm">
      {busy && <div className="flex items-center gap-2 text-primary"><Loader2 className="size-4 animate-spin" />{busy}中</div>}
      {message && !busy && <div className="flex items-center gap-2 text-success"><CheckCircle2 className="size-4" />{message}</div>}
      {error && <div className="flex items-center gap-2 text-error"><AlertTriangle className="size-4" />{error}</div>}
    </div>
  )
}

function ActionButton({ label, icon, disabled, onClick }: { label: string; icon?: React.ReactNode; disabled?: boolean; onClick: () => void }) {
  return <button type="button" disabled={disabled} onClick={onClick} className="inline-flex items-center gap-2 rounded-md border border-outline bg-surface-container px-3 py-2 text-sm text-on-surface hover:bg-surface-container-highest disabled:cursor-not-allowed disabled:opacity-60">{icon}{label}</button>
}

function MetricBlock({ label, metric, tone }: { label: string; metric?: MetricItem; tone: string }) {
  return (
    <div className="rounded-md bg-surface-container px-3 py-3">
      <div className="mb-2 text-xs text-on-surface-variant">{label}</div>
      <div className={`font-mono-num text-lg font-semibold ${tone}`}>{metric?.text || '-'}</div>
    </div>
  )
}

function SuggestionItem({ item }: { item: ReviewSuggestion }) {
  const severityClass = item.severity === 'high' ? 'text-error bg-error/10' : item.severity === 'medium' ? 'text-warning bg-warning/10' : 'text-success bg-success/10'
  return (
    <div className="rounded-md border border-outline bg-surface-container p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-on-surface">{item.title}</h3>
        <span className={`rounded-sm px-2 py-1 text-xs ${severityClass}`}>{severityLabel(item.severity)}</span>
      </div>
      <p className="text-sm leading-6 text-on-surface-variant">{item.content}</p>
    </div>
  )
}

function DataTable({ headers, rows, empty }: { headers: string[]; rows: React.ReactNode[][]; empty: string }) {
  if (!rows.length) return <div className="flex h-64 items-center justify-center rounded-md border border-outline-variant text-sm text-on-surface-variant">{empty}</div>
  return <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-sm"><thead><tr className="border-b border-outline text-xs text-on-surface-variant">{headers.map((header) => <th key={header} className="whitespace-nowrap px-3 py-2 text-left font-medium">{header}</th>)}</tr></thead><tbody className="divide-y divide-outline-variant/40">{rows.map((cells, index) => <tr key={index} className="hover:bg-surface-container-highest">{cells.map((cell, cellIndex) => <td key={cellIndex} className="whitespace-nowrap px-3 py-2 font-mono-num">{cell || '-'}</td>)}</tr>)}</tbody></table></div>
}

function buildChartOption(equity: EquityPoint[], drawdown: DrawdownPoint[]) {
  const styles = getChartStyles()
  const labels = equity.map((point) => point.date || point.time)
  return {
    backgroundColor: 'transparent',
    color: [styles.primary, styles.down],
    tooltip: { trigger: 'axis', backgroundColor: styles.surface, borderColor: styles.outline, textStyle: { color: styles.text } },
    legend: { top: 0, textStyle: { color: styles.variant } },
    grid: [{ left: 48, right: 24, top: 36, height: '48%' }, { left: 48, right: 24, top: '68%', height: '20%' }],
    xAxis: [
      { type: 'category', data: labels, axisLabel: { color: styles.variant }, axisLine: { lineStyle: { color: styles.outline } } },
      { type: 'category', gridIndex: 1, data: labels, axisLabel: { color: styles.variant }, axisLine: { lineStyle: { color: styles.outline } } },
    ],
    yAxis: [
      { type: 'value', axisLabel: { color: styles.variant }, splitLine: { lineStyle: { color: styles.outlineVariant } } },
      { type: 'value', gridIndex: 1, axisLabel: { color: styles.variant, formatter: (value: number) => `${(value * 100).toFixed(0)}%` }, splitLine: { lineStyle: { color: styles.outlineVariant } } },
    ],
    series: [
      {
        name: '净值',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        areaStyle: { opacity: 0.08 },
        data: equity.map((point) => Number(point.equity || 0)),
      },
      {
        name: '回撤',
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex: 1,
        smooth: true,
        symbol: 'none',
        areaStyle: { opacity: 0.12 },
        data: drawdown.map((point) => Number(point.drawdown || 0)),
      },
    ],
  }
}

function getChartStyles() {
  if (typeof window === 'undefined') {
    return { primary: '#3b82f6', down: '#22c55e', surface: '#1a1a2e', outline: '#2a2a3e', outlineVariant: '#1e1e30', text: '#e5e7eb', variant: '#9ca3af' }
  }
  const styles = getComputedStyle(document.documentElement)
  return {
    primary: styles.getPropertyValue('--color-primary').trim(),
    down: styles.getPropertyValue('--color-down').trim(),
    surface: styles.getPropertyValue('--color-surface-container-high').trim(),
    outline: styles.getPropertyValue('--color-outline').trim(),
    outlineVariant: styles.getPropertyValue('--color-outline-variant').trim(),
    text: styles.getPropertyValue('--color-on-surface').trim(),
    variant: styles.getPropertyValue('--color-on-surface-variant').trim(),
  }
}

function money(value?: string | number | null) {
  if (value === null || value === undefined || value === '') return '-'
  const num = Number(value ?? 0)
  if (!Number.isFinite(num)) return '-'
  return `¥${num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function numberText(value?: number) {
  return Number(value ?? 0).toLocaleString('zh-CN')
}

function holdingText(value?: number | null) {
  if (!value) return '-'
  if (value < 60) return `${value} 分钟`
  return `${(value / 60).toFixed(1)} 小时`
}

function pnlClass(value?: string | null) {
  const num = Number(value ?? 0)
  if (num > 0) return 'text-up'
  if (num < 0) return 'text-down'
  return 'text-on-surface'
}

function metricTone(key: string, value?: string | null) {
  const num = Number(value ?? 0)
  if (['total_return', 'realized_pnl', 'win_rate'].includes(key)) return num > 0 ? 'text-up' : num < 0 ? 'text-down' : 'text-on-surface'
  if (key === 'max_drawdown') return num < -0.1 ? 'text-error' : num < -0.05 ? 'text-warning' : 'text-success'
  return 'text-on-surface'
}

function SideText({ side }: { side: string }) {
  const buy = side === 'buy' || side.includes('买')
  const sell = side === 'sell' || side.includes('卖')
  return <span className={buy ? 'text-up' : sell ? 'text-down' : ''}>{buy ? '买入' : sell ? '卖出' : side || '-'}</span>
}

function accountTypeLabel(value: string) {
  if (value === 'live') return '实盘'
  if (value === 'paper') return '模拟盘'
  if (value === 'backtest') return '回测盘'
  return value || '-'
}

function severityLabel(value: string) {
  if (value === 'high') return '高'
  if (value === 'medium') return '中'
  if (value === 'low') return '低'
  return value
}
