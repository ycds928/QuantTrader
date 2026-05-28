import { AppLayout } from '@/common/components'
import request from '@/common/utils/request'
import { Loader2, RefreshCcw } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

type ApiResponse<T> = { success: boolean; data: T; message: string }
type Scope = 'today' | 'history'
type TabKey = 'orders' | 'trades' | 'logs'

type ManagedAccount = {
  id: number
  account_code: string
  account_name: string
  account_type: 'live' | 'paper' | 'backtest'
  status: 'active' | 'inactive' | 'archived'
  is_default: boolean
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

type AutomationLog = {
  id: string
  operation: string
  status: string
  message: string
  created_at: string
}

const apiTimeout = 240000
const inputClass =
  'h-10 rounded-md border border-outline bg-surface-container px-3 text-sm text-on-surface outline-none transition-colors placeholder:text-on-surface-variant focus:border-primary'

export default function OrderQuery() {
  const [activeTab, setActiveTab] = useState<TabKey>('orders')
  const [scope, setScope] = useState<Scope>('today')
  const [accounts, setAccounts] = useState<ManagedAccount[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [orders, setOrders] = useState<OrderRow[]>([])
  const [trades, setTrades] = useState<TradeRow[]>([])
  const [logs, setLogs] = useState<AutomationLog[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [waitCaptcha, setWaitCaptcha] = useState(true)

  const busyText = useMemo(
    () =>
      ({
        accounts: '刷新账户',
        orders: '同步委托',
        trades: '同步成交',
        logs: '刷新日志',
      })[busy || ''] || '',
    [busy]
  )
  const selectedAccount = accounts.find((account) => account.id === selectedAccountId) || null

  useEffect(() => {
    void refreshAccounts()
    void refreshLogs(false)
  }, [])

  async function callApi<T>(label: string, work: () => Promise<ApiResponse<T>>) {
    setBusy(label)
    setMessage('')
    setError('')
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

  async function refreshAccounts() {
    const data = await callApi<ManagedAccount[]>('accounts', () =>
      request.get('/account/accounts', { timeout: apiTimeout }) as Promise<ApiResponse<ManagedAccount[]>>
    )
    if (data) {
      const activeAccounts = data.filter((account) => account.status !== 'archived')
      setAccounts(activeAccounts)
      const defaultAccount = activeAccounts.find((account) => account.is_default)
      const nextAccountId = selectedAccountId || defaultAccount?.id || activeAccounts[0]?.id || null
      setSelectedAccountId(nextAccountId)
      if (nextAccountId) await refreshOrders(scope, nextAccountId)
    }
  }

  async function refreshOrders(nextScope = scope, accountId = selectedAccountId) {
    const data = await callApi<OrderRow[]>('orders', () =>
      request.get('/account/orders', {
        params: {
          scope: nextScope,
          account_id: accountId || undefined,
          wait_manual_captcha: waitCaptcha,
          manual_captcha_timeout: 180,
        },
        timeout: apiTimeout,
      }) as Promise<ApiResponse<OrderRow[]>>
    )
    if (data) setOrders(data)
  }

  async function refreshTrades(nextScope = scope, accountId = selectedAccountId) {
    const data = await callApi<TradeRow[]>('trades', () =>
      request.get('/account/trades', {
        params: {
          scope: nextScope,
          account_id: accountId || undefined,
          wait_manual_captcha: waitCaptcha,
          manual_captcha_timeout: 180,
        },
        timeout: apiTimeout,
      }) as Promise<ApiResponse<TradeRow[]>>
    )
    if (data) setTrades(data)
  }

  async function refreshLogs(showBusy = true) {
    const work = async () =>
      request.get('/account/automation/logs', {
        params: { limit: 60 },
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

  async function refreshActive() {
    if (activeTab === 'orders') await refreshOrders()
    if (activeTab === 'trades') await refreshTrades()
    if (activeTab === 'logs') await refreshLogs()
  }

  async function switchScope(nextScope: Scope) {
    setScope(nextScope)
    if (activeTab === 'orders') await refreshOrders(nextScope)
    if (activeTab === 'trades') await refreshTrades(nextScope)
  }

  async function switchAccount(value: string) {
    const nextAccountId = value ? Number(value) : null
    setSelectedAccountId(nextAccountId)
    setOrders([])
    setTrades([])
    setMessage('')
    setError('')
    if (nextAccountId) {
      if (activeTab === 'orders') await refreshOrders(scope, nextAccountId)
      if (activeTab === 'trades') await refreshTrades(scope, nextAccountId)
    }
  }

  return (
    <AppLayout>
      <div className="space-y-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-on-surface">订单查询</h1>
            <p className="mt-1 text-sm text-on-surface-variant">查询同花顺当日/历史委托、成交记录和自动化日志。</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedAccountId ?? ''}
              onChange={(event) => void switchAccount(event.target.value)}
              className={`${inputClass} min-w-[260px]`}
            >
              <option value="">跟随同花顺当前账户</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.account_name} / {accountTypeLabel(account.account_type)} / {account.account_code}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 rounded-md bg-surface-container px-3 py-2 text-sm text-on-surface-variant">
              <input type="checkbox" checked={waitCaptcha} onChange={(e) => setWaitCaptcha(e.target.checked)} className="size-4 accent-primary" />
              验证码人工等待
            </label>
            <ActionButton label="刷新" icon={<RefreshCcw className="size-4" />} onClick={refreshActive} />
          </div>
        </div>

        {(message || error || busy) && (
          <div className="rounded-md border border-outline bg-surface-container px-4 py-3 text-sm">
            {busy && <div className="flex items-center gap-2 text-primary"><Loader2 className="size-4 animate-spin" />{busyText}中</div>}
            {message && !busy && <div className="text-success">{message}</div>}
            {error && <div className="text-error">{error}</div>}
          </div>
        )}

        <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
          <div className="mb-3 rounded-md bg-surface-container px-3 py-2 text-xs text-on-surface-variant">
            {selectedAccount
              ? `当前查询账户：${selectedAccount.account_name}（${accountTypeLabel(selectedAccount.account_type)}）。${selectedAccount.account_type === 'live' ? '委托/成交会从同花顺同步后保存。' : '委托/成交直接从本地持久化表读取。'}`
              : '未选择账户时，查询跟随同花顺当前登录账户。'}
          </div>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-1 rounded-md bg-surface-container p-1">
              <TabButton active={activeTab === 'orders'} label="委托" onClick={() => setActiveTab('orders')} />
              <TabButton active={activeTab === 'trades'} label="成交" onClick={() => setActiveTab('trades')} />
              <TabButton active={activeTab === 'logs'} label="日志" onClick={() => setActiveTab('logs')} />
            </div>
            {activeTab !== 'logs' && (
              <div className="flex flex-wrap gap-1 rounded-md bg-surface-container p-1">
                <TabButton active={scope === 'today'} label="当日" onClick={() => switchScope('today')} />
                <TabButton active={scope === 'history'} label="历史" onClick={() => switchScope('history')} />
              </div>
            )}
          </div>

          {activeTab === 'orders' && <OrdersTable rows={orders} />}
          {activeTab === 'trades' && <TradesTable rows={trades} />}
          {activeTab === 'logs' && <LogsTable rows={logs} />}
        </section>
      </div>
    </AppLayout>
  )
}

function ActionButton({ label, icon, onClick }: { label: string; icon?: React.ReactNode; onClick: () => void }) {
  return <button type="button" onClick={onClick} className="inline-flex items-center gap-2 rounded-md border border-outline bg-surface-container px-3 py-2 text-sm text-on-surface hover:bg-surface-container-highest">{icon}{label}</button>
}

function TabButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`rounded-sm px-3 py-2 text-sm ${active ? 'bg-primary/15 text-primary' : 'text-on-surface-variant hover:bg-surface-container-high'}`}>{label}</button>
}

function OrdersTable({ rows }: { rows: OrderRow[] }) {
  return <DataTable empty="暂无委托记录" headers={['合同编号', '代码', '名称', '方向', '价格', '数量', '成交', '状态', '时间']} rows={rows.map((row) => [row.broker_order_id || row.order_id, row.symbol, row.name, <SideText side={row.side} />, money(row.price), numberText(row.quantity), numberText(row.filled_quantity), orderStatusLabel(row.status), row.submitted_at || '-'])} />
}

function TradesTable({ rows }: { rows: TradeRow[] }) {
  return <DataTable empty="暂无成交记录" headers={['成交编号', '合同编号', '代码', '名称', '方向', '价格', '数量', '金额', '时间']} rows={rows.map((row) => [row.broker_trade_id || row.trade_id, row.order_id, row.symbol, row.name, <SideText side={row.side} />, money(row.price), numberText(row.quantity), money(row.amount), row.traded_at || '-'])} />
}

function LogsTable({ rows }: { rows: AutomationLog[] }) {
  return <DataTable empty="暂无自动化日志" headers={['时间', '操作', '状态', '信息']} rows={rows.map((row) => [row.created_at, row.operation, <span className={row.status === 'success' ? 'text-success' : 'text-warning'}>{row.status}</span>, row.message])} />
}

function DataTable({ headers, rows, empty }: { headers: string[]; rows: React.ReactNode[][]; empty: string }) {
  if (!rows.length) return <div className="flex h-64 items-center justify-center rounded-md border border-outline-variant text-sm text-on-surface-variant">{empty}</div>
  return <div className="overflow-x-auto"><table className="w-full min-w-[860px] text-sm"><thead><tr className="border-b border-outline text-xs text-on-surface-variant">{headers.map((h) => <th key={h} className="whitespace-nowrap px-3 py-2 text-left font-medium">{h}</th>)}</tr></thead><tbody className="divide-y divide-outline-variant/40">{rows.map((cells, i) => <tr key={i} className="hover:bg-surface-container-highest">{cells.map((cell, j) => <td key={j} className="whitespace-nowrap px-3 py-2 font-mono-num">{cell || '-'}</td>)}</tr>)}</tbody></table></div>
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

function accountTypeLabel(value: string) {
  if (value === 'live') return '实盘'
  if (value === 'paper') return '模拟盘'
  if (value === 'backtest') return '回测盘'
  return value || '-'
}

function orderStatusLabel(status: string) {
  const value = String(status || 'submitted').toLowerCase()
  if (['全部撤单', '已撤', 'canceled', 'cancelled'].some((item) => value.includes(item.toLowerCase()))) return '全部撤单'
  if (['部分撤单', '部撤', 'partial_canceled'].some((item) => value.includes(item.toLowerCase()))) return '部分撤单'
  if (['全部成交', '已成', 'filled'].some((item) => value.includes(item.toLowerCase()))) return '全部成交'
  if (['部分成交', '部成', 'partial_filled'].some((item) => value.includes(item.toLowerCase()))) return '部分成交'
  if (['撤单中', 'cancel_pending'].some((item) => value.includes(item.toLowerCase()))) return '撤单中'
  if (['部分失效', 'partial_expired'].some((item) => value.includes(item.toLowerCase()))) return '部分成交后失效'
  if (['已失效', '失效', 'expired'].some((item) => value.includes(item.toLowerCase()))) return '已失效'
  if (['废单', 'rejected'].some((item) => value.includes(item.toLowerCase()))) return '废单'
  if (['失败', 'failed'].some((item) => value.includes(item.toLowerCase()))) return '失败'
  if (['已提交未成交', '未成交', '已报', 'submitted', 'created', 'accepted'].some((item) => value.includes(item.toLowerCase()))) return '已提交未成交'
  return status || '-'
}
