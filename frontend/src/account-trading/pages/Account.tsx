import { AppLayout } from '@/common/components'
import request from '@/common/utils/request'
import {
  Activity,
  Ban,
  ClipboardList,
  Loader2,
  RefreshCcw,
  ShieldCheck,
  Wallet,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

type ApiResponse<T> = {
  success: boolean
  data: T
  message: string
}

type Balance = {
  account_id: string
  mode: string
  total_asset: string
  available_cash: string
  withdrawable_cash: string
  market_value: string
  cash_balance: string
  frozen_cash: string
  updated_at: string
}

type Position = {
  position_id: string
  symbol: string
  name: string
  quantity: number
  available_quantity: number
  cost_price: string
  last_price: string
  market_value: string
  unrealized_pnl: string
}

type OrderRow = {
  order_id: string
  broker_order_id: string
  symbol: string
  name: string
  side: string
  price: string
  quantity: number
  filled_quantity: number
  avg_fill_price: string
  status: string
  submitted_at: string
}

type TradeRow = {
  trade_id: string
  broker_trade_id: string
  order_id: string
  symbol: string
  name: string
  side: string
  price: string
  quantity: number
  amount: string
  traded_at: string
}

type AutomationStatus = {
  connected: boolean
  ready: boolean
  window_title: string
  window_class: string
  window_rect: string
  account?: AccountInfo
}

type AccountInfo = {
  account_name: string
  account_type: 'paper' | 'live' | 'unknown'
  account_type_label: string
  market: string
  shareholder_account: string
  capital_account: string
}

type AutomationLog = {
  id: string
  operation: string
  status: string
  message: string
  created_at: string
}

type TabKey = 'positions' | 'orders' | 'trades' | 'logs'

const apiTimeout = 240000
const inputClass =
  'h-10 w-full rounded-md border border-outline bg-surface-container px-3 text-sm text-on-surface outline-none transition-colors placeholder:text-on-surface-variant focus:border-primary'

export default function Account() {
  const [balance, setBalance] = useState<Balance | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<OrderRow[]>([])
  const [trades, setTrades] = useState<TradeRow[]>([])
  const [logs, setLogs] = useState<AutomationLog[]>([])
  const [status, setStatus] = useState<AutomationStatus | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>('positions')
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [waitCaptcha, setWaitCaptcha] = useState(true)
  const [orderForm, setOrderForm] = useState({
    side: 'buy' as 'buy' | 'sell',
    symbol: '301183',
    price: '',
    quantity: '100',
    remark: '',
  })
  const [cancelEntrustNo, setCancelEntrustNo] = useState('')

  const busyLabel = useMemo(() => {
    if (!busy) return ''
    return {
      status: '检查连接',
      balance: '同步资金',
      positions: '同步持仓',
      orders: '同步委托',
      trades: '同步成交',
      sync: '全量同步',
      order: '提交委托',
      cancel: '执行撤单',
      logs: '刷新日志',
    }[busy]
  }, [busy])

  useEffect(() => {
    void refreshStatus()
    void refreshLogs()
  }, [])

  async function callApi<T>(label: string, work: () => Promise<ApiResponse<T>>) {
    setBusy(label)
    setError('')
    setMessage('')
    try {
      const response = await work()
      setMessage(response.message)
      await refreshLogs(false)
      return response.data
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      const text = detail?.message || err?.message || '请求失败'
      const captchaPath = detail?.captcha_path ? ` 验证码截图：${detail.captcha_path}` : ''
      setError(`${text}${captchaPath}`)
      await refreshLogs(false)
      return null
    } finally {
      setBusy(null)
    }
  }

  async function refreshStatus() {
    const data = await callApi<AutomationStatus>('status', () =>
      request.get('/account/automation/status', { timeout: apiTimeout }) as Promise<ApiResponse<AutomationStatus>>
    )
    if (data) setStatus(data)
  }

  async function refreshBalance() {
    const data = await callApi<Balance>('balance', () =>
      request.get('/account/balance', {
        params: captchaParams(),
        timeout: apiTimeout,
      }) as Promise<ApiResponse<Balance>>
    )
    if (data) setBalance(data)
  }

  async function refreshPositions() {
    const data = await callApi<Position[]>('positions', () =>
      request.get('/account/positions', {
        params: captchaParams(),
        timeout: apiTimeout,
      }) as Promise<ApiResponse<Position[]>>
    )
    if (data) setPositions(data)
  }

  async function refreshOrders() {
    const data = await callApi<OrderRow[]>('orders', () =>
      request.get('/account/orders', {
        params: { scope: 'today', ...captchaParams() },
        timeout: apiTimeout,
      }) as Promise<ApiResponse<OrderRow[]>>
    )
    if (data) setOrders(data)
  }

  async function refreshTrades() {
    const data = await callApi<TradeRow[]>('trades', () =>
      request.get('/account/trades', {
        params: { scope: 'today', ...captchaParams() },
        timeout: apiTimeout,
      }) as Promise<ApiResponse<TradeRow[]>>
    )
    if (data) setTrades(data)
  }

  async function refreshLogs(showBusy = true) {
    const work = async () =>
      request.get('/account/automation/logs', {
        params: { limit: 30 },
        timeout: apiTimeout,
      }) as Promise<ApiResponse<AutomationLog[]>>
    if (!showBusy) {
      const response = await work()
      setLogs(response.data)
      return
    }
    const data = await callApi<AutomationLog[]>('logs', work)
    if (data) setLogs(data)
  }

  async function syncAccount() {
    const data = await callApi<{
      balance: Balance
      positions: Position[]
      orders: OrderRow[]
      trades: TradeRow[]
    }>('sync', () =>
      request.post(
        '/account/sync',
        { wait_manual_captcha: waitCaptcha, manual_captcha_timeout: 180 },
        { timeout: apiTimeout }
      ) as Promise<ApiResponse<{ balance: Balance; positions: Position[]; orders: OrderRow[]; trades: TradeRow[] }>>
    )
    if (data) {
      setBalance(data.balance)
      setPositions(data.positions)
      setOrders(data.orders)
      setTrades(data.trades)
    }
  }

  async function submitOrder(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = await callApi<Record<string, unknown>>('order', () =>
      request.post(
        '/account/order',
        {
          symbol: orderForm.symbol.trim(),
          side: orderForm.side,
          price: orderForm.price.trim(),
          quantity: Number(orderForm.quantity),
          mode: 'live',
          idempotency_key: crypto.randomUUID(),
          remark: orderForm.remark.trim() || undefined,
          wait_manual_captcha: waitCaptcha,
          manual_captcha_timeout: 180,
        },
        { timeout: apiTimeout }
      ) as Promise<ApiResponse<Record<string, unknown>>>
    )
    if (data) {
      await refreshOrders()
      setActiveTab('orders')
    }
  }

  async function submitCancel(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!cancelEntrustNo.trim()) return
    const data = await callApi<Record<string, unknown>>('cancel', () =>
      request.post(
        `/account/order/${encodeURIComponent(cancelEntrustNo.trim())}/cancel`,
        { wait_manual_captcha: waitCaptcha, manual_captcha_timeout: 180 },
        { timeout: apiTimeout }
      ) as Promise<ApiResponse<Record<string, unknown>>>
    )
    if (data) {
      await refreshOrders()
      setActiveTab('orders')
    }
  }

  function captchaParams() {
    return {
      wait_manual_captcha: waitCaptcha,
      manual_captcha_timeout: 180,
    }
  }

  return (
    <AppLayout>
      <div className="space-y-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-on-surface">账户与交易对接</h1>
            <p className="mt-1 text-sm text-on-surface-variant">
              本机同花顺桌面自动化：资金、持仓、委托、成交、买卖、撤单。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 rounded-md bg-surface-container px-3 py-2 text-sm text-on-surface-variant">
              <input
                type="checkbox"
                checked={waitCaptcha}
                onChange={(event) => setWaitCaptcha(event.target.checked)}
                className="size-4 accent-primary"
              />
              验证码人工等待
            </label>
            <ActionButton label="连接" icon={<ShieldCheck className="size-4" />} onClick={refreshStatus} />
            <ActionButton label="同步" icon={<RefreshCcw className="size-4" />} onClick={syncAccount} />
          </div>
        </div>

        {(message || error || busy) && (
          <div className="rounded-md border border-outline bg-surface-container px-4 py-3 text-sm">
            {busy && (
              <div className="flex items-center gap-2 text-primary">
                <Loader2 className="size-4 animate-spin" />
                {busyLabel}中；如同花顺弹出验证码，请在桌面弹窗内输入并确认。
              </div>
            )}
            {message && !busy && <div className="text-success">{message}</div>}
            {error && <div className="text-error">{error}</div>}
          </div>
        )}

        <div className="grid gap-4 xl:grid-cols-4">
          <MetricCard label="总资产" value={money(balance?.total_asset)} icon={<Wallet className="size-5" />} />
          <MetricCard label="可用资金" value={money(balance?.available_cash)} icon={<Activity className="size-5" />} />
          <MetricCard label="股票市值" value={money(balance?.market_value)} icon={<ClipboardList className="size-5" />} />
          <MetricCard label="冻结资金" value={money(balance?.frozen_cash)} icon={<Ban className="size-5" />} />
        </div>

        <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">当前交易账户</h2>
            <span
              className={`rounded-sm px-2 py-1 text-xs font-medium ${
                status?.account?.account_type === 'live'
                  ? 'bg-error/15 text-error'
                  : status?.account?.account_type === 'paper'
                    ? 'bg-primary/15 text-primary'
                    : 'bg-warning/15 text-warning'
              }`}
            >
              {status?.account?.account_type_label || '未知'}
            </span>
          </div>
          <div className="grid gap-3 text-sm md:grid-cols-4">
            <AccountInfoItem label="账户名称" value={status?.account?.account_name || '-'} />
            <AccountInfoItem label="资金账户" value={status?.account?.capital_account || '-'} />
            <AccountInfoItem label="股东账号" value={status?.account?.shareholder_account || '-'} />
            <AccountInfoItem label="交易市场" value={status?.account?.market || '-'} />
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-[minmax(320px,420px)_1fr]">
          <div className="space-y-4">
            <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-semibold">实盘委托</h2>
                <span className="rounded-sm bg-error/10 px-2 py-1 text-xs text-error">LIVE</span>
              </div>
              <form className="space-y-3" onSubmit={submitOrder}>
                <div className="grid grid-cols-2 gap-2 rounded-md bg-surface-container p-1">
                  {(['buy', 'sell'] as const).map((side) => (
                    <button
                      key={side}
                      type="button"
                      onClick={() => setOrderForm((prev) => ({ ...prev, side }))}
                      className={`rounded-sm px-3 py-2 text-sm font-medium transition-colors ${
                        orderForm.side === side
                          ? side === 'buy'
                            ? 'bg-up/15 text-up'
                            : 'bg-down/15 text-down'
                          : 'text-on-surface-variant hover:bg-surface-container-high'
                      }`}
                    >
                      {side === 'buy' ? '买入' : '卖出'}
                    </button>
                  ))}
                </div>
                <Field label="证券代码">
                  <input
                    value={orderForm.symbol}
                    onChange={(event) => setOrderForm((prev) => ({ ...prev, symbol: event.target.value }))}
                    className={inputClass}
                    placeholder="301183"
                    required
                  />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="委托价格">
                    <input
                      value={orderForm.price}
                      onChange={(event) => setOrderForm((prev) => ({ ...prev, price: event.target.value }))}
                      className={`${inputClass} font-mono-num`}
                      placeholder="240.70"
                      required
                    />
                  </Field>
                  <Field label="委托数量">
                    <input
                      value={orderForm.quantity}
                      onChange={(event) => setOrderForm((prev) => ({ ...prev, quantity: event.target.value }))}
                      className={`${inputClass} font-mono-num`}
                      placeholder="100"
                      required
                    />
                  </Field>
                </div>
                <Field label="备注">
                  <input
                    value={orderForm.remark}
                    onChange={(event) => setOrderForm((prev) => ({ ...prev, remark: event.target.value }))}
                    className={inputClass}
                    placeholder="人工委托"
                  />
                </Field>
                <button
                  type="submit"
                  disabled={Boolean(busy)}
                  className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-on-primary disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {busy === 'order' && <Loader2 className="size-4 animate-spin" />}
                  提交委托
                </button>
              </form>
            </section>

            <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
              <h2 className="mb-4 text-sm font-semibold">撤单</h2>
              <form className="space-y-3" onSubmit={submitCancel}>
                <Field label="合同编号">
                  <input
                    value={cancelEntrustNo}
                    onChange={(event) => setCancelEntrustNo(event.target.value)}
                    className={`${inputClass} font-mono-num`}
                    placeholder="5963530617"
                    required
                  />
                </Field>
                <button
                  type="submit"
                  disabled={Boolean(busy)}
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-error/50 px-4 py-2.5 text-sm font-semibold text-error hover:bg-error/10 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {busy === 'cancel' && <Loader2 className="size-4 animate-spin" />}
                  执行撤单
                </button>
              </form>
            </section>

            <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
              <h2 className="mb-3 text-sm font-semibold">连接状态</h2>
              <dl className="space-y-2 text-xs">
                <InfoRow label="进程" value={status?.connected ? '已连接' : '未连接'} />
                <InfoRow label="交易页" value={status?.ready ? '已就绪' : '需登录/未就绪'} />
                <InfoRow label="账户类型" value={status?.account?.account_type_label || '-'} />
                <InfoRow label="资金账户" value={status?.account?.capital_account || '-'} />
                <InfoRow label="窗口" value={status?.window_title || '-'} />
                <InfoRow label="区域" value={status?.window_rect || '-'} />
                <InfoRow label="更新时间" value={balance?.updated_at || '-'} />
              </dl>
            </section>
          </div>

          <section className="min-w-0 rounded-lg bg-surface-container-high p-4 shadow-card">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-1 rounded-md bg-surface-container p-1">
                <TabButton active={activeTab === 'positions'} label="持仓" onClick={() => setActiveTab('positions')} />
                <TabButton active={activeTab === 'orders'} label="当日委托" onClick={() => setActiveTab('orders')} />
                <TabButton active={activeTab === 'trades'} label="当日成交" onClick={() => setActiveTab('trades')} />
                <TabButton active={activeTab === 'logs'} label="日志" onClick={() => setActiveTab('logs')} />
              </div>
              <div className="flex flex-wrap gap-2">
                {activeTab === 'positions' && <ActionButton label="刷新持仓" onClick={refreshPositions} />}
                {activeTab === 'orders' && <ActionButton label="刷新委托" onClick={refreshOrders} />}
                {activeTab === 'trades' && <ActionButton label="刷新成交" onClick={refreshTrades} />}
                {activeTab === 'logs' && <ActionButton label="刷新日志" onClick={() => refreshLogs()} />}
                <ActionButton label="刷新资金" onClick={refreshBalance} />
              </div>
            </div>

            {activeTab === 'positions' && <PositionsTable rows={positions} />}
            {activeTab === 'orders' && <OrdersTable rows={orders} onCancel={(id) => setCancelEntrustNo(id)} />}
            {activeTab === 'trades' && <TradesTable rows={trades} />}
            {activeTab === 'logs' && <LogsTable rows={logs} />}
          </section>
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

function MetricCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-surface-container-high p-4 shadow-card">
      <div className="mb-3 flex items-center justify-between text-on-surface-variant">
        <span className="text-xs">{label}</span>
        {icon}
      </div>
      <div className="font-mono-num text-xl font-semibold text-on-surface">{value}</div>
    </div>
  )
}

function ActionButton({ label, icon, onClick }: { label: string; icon?: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-2 rounded-md border border-outline bg-surface-container px-3 py-2 text-sm text-on-surface hover:bg-surface-container-highest"
    >
      {icon}
      {label}
    </button>
  )
}

function TabButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-sm px-3 py-2 text-sm transition-colors ${
        active ? 'bg-primary/15 text-primary' : 'text-on-surface-variant hover:bg-surface-container-high'
      }`}
    >
      {label}
    </button>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[72px_1fr] gap-2">
      <dt className="text-on-surface-variant">{label}</dt>
      <dd className="truncate text-on-surface">{value}</dd>
    </div>
  )
}

function AccountInfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-surface-container px-3 py-2">
      <div className="mb-1 text-xs text-on-surface-variant">{label}</div>
      <div className="truncate font-mono-num text-sm text-on-surface">{value}</div>
    </div>
  )
}

function PositionsTable({ rows }: { rows: Position[] }) {
  return (
    <DataTable
      empty="暂无持仓数据"
      headers={['代码', '名称', '持仓', '可卖', '成本', '现价', '市值', '浮盈']}
      rows={rows.map((row) => [
        row.symbol,
        row.name,
        numberText(row.quantity),
        numberText(row.available_quantity),
        money(row.cost_price),
        money(row.last_price),
        money(row.market_value),
        <span className={pnlClass(row.unrealized_pnl)}>{money(row.unrealized_pnl)}</span>,
      ])}
    />
  )
}

function OrdersTable({ rows, onCancel }: { rows: OrderRow[]; onCancel: (id: string) => void }) {
  return (
    <DataTable
      empty="暂无当日委托"
      headers={['合同编号', '代码', '名称', '方向', '价格', '数量', '成交', '状态', '操作']}
      rows={rows.map((row) => [
        row.broker_order_id || row.order_id,
        row.symbol,
        row.name,
        <SideText side={row.side} />,
        money(row.price),
        numberText(row.quantity),
        numberText(row.filled_quantity),
        row.status || '-',
        <button
          type="button"
          onClick={() => onCancel(row.broker_order_id || row.order_id)}
          className="rounded-sm px-2 py-1 text-xs text-error hover:bg-error/10"
        >
          填入撤单
        </button>,
      ])}
    />
  )
}

function TradesTable({ rows }: { rows: TradeRow[] }) {
  return (
    <DataTable
      empty="暂无当日成交"
      headers={['成交编号', '代码', '名称', '方向', '价格', '数量', '金额', '时间']}
      rows={rows.map((row) => [
        row.broker_trade_id || row.trade_id,
        row.symbol,
        row.name,
        <SideText side={row.side} />,
        money(row.price),
        numberText(row.quantity),
        money(row.amount),
        row.traded_at || '-',
      ])}
    />
  )
}

function LogsTable({ rows }: { rows: AutomationLog[] }) {
  return (
    <DataTable
      empty="暂无自动化日志"
      headers={['时间', '操作', '状态', '信息']}
      rows={rows.map((row) => [
        row.created_at,
        row.operation,
        <span className={row.status === 'success' ? 'text-success' : 'text-warning'}>{row.status}</span>,
        row.message,
      ])}
    />
  )
}

function DataTable({
  headers,
  rows,
  empty,
}: {
  headers: string[]
  rows: React.ReactNode[][]
  empty: string
}) {
  if (!rows.length) {
    return (
      <div className="flex h-64 items-center justify-center rounded-md border border-outline-variant text-sm text-on-surface-variant">
        {empty}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-sm">
        <thead>
          <tr className="border-b border-outline text-xs text-on-surface-variant">
            {headers.map((header) => (
              <th key={header} className="whitespace-nowrap px-3 py-2 text-left font-medium">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/40">
          {rows.map((cells, index) => (
            <tr key={index} className="hover:bg-surface-container-highest">
              {cells.map((cell, cellIndex) => (
                <td key={cellIndex} className="whitespace-nowrap px-3 py-2 font-mono-num">
                  {cell || '-'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SideText({ side }: { side: string }) {
  const buy = side === 'buy' || side.includes('买')
  const sell = side === 'sell' || side.includes('卖')
  return <span className={buy ? 'text-up' : sell ? 'text-down' : ''}>{buy ? '买入' : sell ? '卖出' : side || '-'}</span>
}

function money(value?: string | number) {
  const num = Number(value ?? 0)
  if (!Number.isFinite(num)) return '-'
  return `¥${num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function numberText(value?: number) {
  return Number(value ?? 0).toLocaleString('zh-CN')
}

function pnlClass(value?: string) {
  const num = Number(value ?? 0)
  if (num > 0) return 'text-up'
  if (num < 0) return 'text-down'
  return 'text-on-surface'
}
