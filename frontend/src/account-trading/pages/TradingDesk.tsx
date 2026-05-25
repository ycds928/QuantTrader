import { AppLayout } from '@/common/components'
import request from '@/common/utils/request'
import { Activity, Ban, ClipboardList, Loader2, RefreshCcw, ShieldCheck, Wallet } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

type ApiResponse<T> = { success: boolean; data: T; message: string }
type Balance = {
  total_asset: string
  available_cash: string
  withdrawable_cash: string
  market_value: string
  cash_balance: string
  frozen_cash: string
  updated_at: string
}
type Position = {
  symbol: string
  name: string
  quantity: number
  available_quantity: number
  cost_price: string
  last_price: string
  market_value: string
  unrealized_pnl: string
}
type Scope = 'today' | 'history'
type WorkspaceTab = 'positions' | 'orders' | 'trades' | 'logs'
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
type AutomationStatus = {
  connected: boolean
  ready: boolean
  window_title: string
  window_rect: string
  account?: {
    account_name: string
    account_type: 'paper' | 'live' | 'unknown'
    account_type_label: string
    market: string
    shareholder_account: string
    capital_account: string
  }
}

type ManagedAccount = {
  id: number
  account_code: string
  account_name: string
  account_type: 'live' | 'paper' | 'backtest'
  broker_name: string | null
  broker_account_no: string | null
  shareholder_account: string | null
  exchange: string | null
  status: 'active' | 'inactive' | 'archived'
  is_default: boolean
}

const apiTimeout = 240000
const inputClass =
  'h-10 w-full rounded-md border border-outline bg-surface-container px-3 text-sm text-on-surface outline-none transition-colors placeholder:text-on-surface-variant focus:border-primary'

export default function TradingDesk() {
  const [accounts, setAccounts] = useState<ManagedAccount[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [balance, setBalance] = useState<Balance | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>('positions')
  const [scope, setScope] = useState<Scope>('today')
  const [orders, setOrders] = useState<OrderRow[]>([])
  const [trades, setTrades] = useState<TradeRow[]>([])
  const [logs, setLogs] = useState<AutomationLog[]>([])
  const [status, setStatus] = useState<AutomationStatus | null>(null)
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

  const busyText = useMemo(
    () =>
      ({
        status: '检查连接',
        sync: '同步账户',
        order: '提交委托',
        cancel: '执行撤单',
        orders: '查询委托',
        trades: '查询成交',
        logs: '刷新日志',
      })[busy || ''] || '',
    [busy]
  )
  const selectedAccount = accounts.find((account) => account.id === selectedAccountId) || null
  const selectedAccountTradeable = !selectedAccount || selectedAccount.account_type === 'live' || selectedAccount.account_type === 'paper'

  useEffect(() => {
    void refreshAccounts()
    void refreshStatus()
    void refreshLogs(false)
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

  async function refreshStatus() {
    const data = await callApi<AutomationStatus>('status', () =>
      request.get('/account/automation/status', { timeout: apiTimeout }) as Promise<ApiResponse<AutomationStatus>>
    )
    if (data) setStatus(data)
  }

  async function refreshAccounts() {
    const data = await callApi<ManagedAccount[]>('accounts', () =>
      request.get('/account/accounts', { timeout: apiTimeout }) as Promise<ApiResponse<ManagedAccount[]>>
    )
    if (data) {
      setAccounts(data.filter((account) => account.status !== 'archived'))
      const defaultAccount = data.find((account) => account.is_default && account.status !== 'archived')
      const firstActive = data.find((account) => account.status !== 'archived')
      setSelectedAccountId((current) => current || defaultAccount?.id || firstActive?.id || null)
    }
  }

  async function syncAccount() {
    if (selectedAccount && !selectedAccountTradeable) {
      setError('当前选择的账户暂不支持交易台同步。')
      return
    }
    const data = await callApi<{ balance: Balance; positions: Position[] }>('sync', () =>
      request.post(
        '/account/sync',
        {
          account_id: selectedAccountId || undefined,
          wait_manual_captcha: waitCaptcha,
          manual_captcha_timeout: 180,
        },
        { timeout: apiTimeout }
      ) as Promise<ApiResponse<{ balance: Balance; positions: Position[] }>>
    )
    if (data) {
      setBalance(data.balance)
      setPositions(data.positions)
      await refreshOrders('today')
      await refreshTrades('today')
    }
  }

  async function refreshOrders(nextScope = scope) {
    const data = await callApi<OrderRow[]>('orders', () =>
      request.get('/account/orders', {
        params: {
          scope: nextScope,
          account_id: selectedAccountId || undefined,
          wait_manual_captcha: waitCaptcha,
          manual_captcha_timeout: 180,
        },
        timeout: apiTimeout,
      }) as Promise<ApiResponse<OrderRow[]>>
    )
    if (data) setOrders(data)
  }

  async function refreshTrades(nextScope = scope) {
    const data = await callApi<TradeRow[]>('trades', () =>
      request.get('/account/trades', {
        params: {
          scope: nextScope,
          account_id: selectedAccountId || undefined,
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

  async function submitOrder(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (selectedAccount && !selectedAccountTradeable) {
      setError('当前选择的账户暂不支持交易台下单。')
      return
    }
    const mode = selectedAccount?.account_type === 'paper' ? 'paper' : 'live'
    const data = await callApi<Record<string, unknown>>('order', () =>
      request.post(
        '/account/order',
        {
          symbol: orderForm.symbol.trim(),
          side: orderForm.side,
          price: orderForm.price.trim(),
          quantity: Number(orderForm.quantity),
          mode,
          account_id: selectedAccountId || undefined,
          idempotency_key: mode === 'live' ? crypto.randomUUID() : undefined,
          remark: orderForm.remark.trim() || undefined,
          wait_manual_captcha: waitCaptcha,
          manual_captcha_timeout: 180,
        },
        { timeout: apiTimeout }
      ) as Promise<ApiResponse<Record<string, unknown>>>
    )
    if (data) await syncAccount()
  }

  async function refreshWorkspace() {
    if (workspaceTab === 'positions') await syncAccount()
    if (workspaceTab === 'orders') await refreshOrders()
    if (workspaceTab === 'trades') await refreshTrades()
    if (workspaceTab === 'logs') await refreshLogs()
  }

  async function switchScope(nextScope: Scope) {
    setScope(nextScope)
    if (workspaceTab === 'orders') await refreshOrders(nextScope)
    if (workspaceTab === 'trades') await refreshTrades(nextScope)
  }

  function switchAccount(value: string) {
    setSelectedAccountId(value ? Number(value) : null)
    setBalance(null)
    setPositions([])
    setOrders([])
    setTrades([])
    setMessage('')
    setError('')
  }

  async function submitCancel(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!cancelEntrustNo.trim()) return
    if (selectedAccount && selectedAccount.account_type !== 'live') {
      setError('模拟账户当前按委托价立即成交，暂不提供撤单。')
      return
    }
    const data = await callApi<Record<string, unknown>>('cancel', () =>
      request.post(
        `/account/order/${encodeURIComponent(cancelEntrustNo.trim())}/cancel`,
        {
          account_id: selectedAccountId || undefined,
          wait_manual_captcha: waitCaptcha,
          manual_captcha_timeout: 180,
        },
        { timeout: apiTimeout }
      ) as Promise<ApiResponse<Record<string, unknown>>>
    )
    if (data) await syncAccount()
  }

  return (
    <AppLayout>
      <div className="space-y-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-on-surface">交易界面</h1>
            <p className="mt-1 text-sm text-on-surface-variant">实盘连接同花顺交易端，模拟盘按委托价立即成交并更新账户记录。</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 rounded-md bg-surface-container px-3 py-2 text-sm text-on-surface-variant">
              <input type="checkbox" checked={waitCaptcha} onChange={(e) => setWaitCaptcha(e.target.checked)} className="size-4 accent-primary" />
              验证码人工等待
            </label>
            <ActionButton label="连接" icon={<ShieldCheck className="size-4" />} onClick={refreshStatus} />
            <ActionButton label="同步" icon={<RefreshCcw className="size-4" />} onClick={syncAccount} disabled={!selectedAccountTradeable} />
          </div>
        </div>

        {(message || error || busy) && <Notice busy={busyText} message={message} error={error} />}

        <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">交易账户</h2>
            <span className={`rounded-sm px-2 py-1 text-xs font-medium ${status?.account?.account_type === 'live' ? 'bg-error/15 text-error' : 'bg-primary/15 text-primary'}`}>
              {status?.account?.account_type_label || '未知'}
            </span>
          </div>
          <div className="mb-3 grid gap-3 text-sm md:grid-cols-[minmax(220px,360px)_1fr]">
            <label className="block">
              <span className="mb-1 block text-xs text-on-surface-variant">选择账户</span>
              <select
                value={selectedAccountId ?? ''}
                onChange={(event) => switchAccount(event.target.value)}
                className={inputClass}
              >
                <option value="">跟随同花顺当前账户</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.account_name} / {accountTypeLabel(account.account_type)} / {account.account_code}
                  </option>
                ))}
              </select>
            </label>
            <div className="rounded-md bg-surface-container px-3 py-2 text-xs text-on-surface-variant">
              {selectedAccount
                ? `已选择：${selectedAccount.account_name}（${accountTypeLabel(selectedAccount.account_type)}）。${selectedAccount.account_type === 'paper' ? '模拟交易会按委托价立即成交。' : selectedAccount.account_type === 'live' ? '实盘交易会通过同花顺桌面自动化执行。' : '该类型暂不支持交易台下单。'}`
                : '未选择账户时，交易操作跟随同花顺当前登录账户。'}
            </div>
          </div>
          <div className="grid gap-3 text-sm md:grid-cols-4">
            <InfoBlock label="账户名称" value={status?.account?.account_name || '-'} />
            <InfoBlock label="资金账户" value={status?.account?.capital_account || '-'} />
            <InfoBlock label="股东账号" value={status?.account?.shareholder_account || '-'} />
            <InfoBlock label="交易市场" value={status?.account?.market || '-'} />
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-4">
          <MetricCard label="总资产" value={money(balance?.total_asset)} icon={<Wallet className="size-5" />} />
          <MetricCard label="可用资金" value={money(balance?.available_cash)} icon={<Activity className="size-5" />} />
          <MetricCard label="股票市值" value={money(balance?.market_value)} icon={<ClipboardList className="size-5" />} />
          <MetricCard label="冻结资金" value={money(balance?.frozen_cash)} icon={<Ban className="size-5" />} />
        </div>

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
                      disabled={!selectedAccountTradeable}
                      onClick={() => setOrderForm((prev) => ({ ...prev, side }))}
                      className={`rounded-sm px-3 py-2 text-sm font-medium ${orderForm.side === side ? (side === 'buy' ? 'bg-up/15 text-up' : 'bg-down/15 text-down') : 'text-on-surface-variant hover:bg-surface-container-high'}`}
                    >
                      {side === 'buy' ? '买入' : '卖出'}
                    </button>
                  ))}
                </div>
                <Field label="证券代码">
                  <input value={orderForm.symbol} onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value })} className={inputClass} required />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="委托价格">
                    <input value={orderForm.price} onChange={(e) => setOrderForm({ ...orderForm, price: e.target.value })} className={`${inputClass} font-mono-num`} placeholder="240.70" required />
                  </Field>
                  <Field label="委托数量">
                    <input value={orderForm.quantity} onChange={(e) => setOrderForm({ ...orderForm, quantity: e.target.value })} className={`${inputClass} font-mono-num`} required />
                  </Field>
                </div>
                <Field label="备注">
                  <input value={orderForm.remark} onChange={(e) => setOrderForm({ ...orderForm, remark: e.target.value })} className={inputClass} placeholder="人工委托" />
                </Field>
                <button type="submit" disabled={Boolean(busy) || !selectedAccountTradeable} className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-on-primary disabled:cursor-not-allowed disabled:opacity-60">
                  {busy === 'order' && <Loader2 className="size-4 animate-spin" />}
                  提交委托
                </button>
              </form>
            </section>

            <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
              <h2 className="mb-4 text-sm font-semibold">撤单</h2>
              <form className="space-y-3" onSubmit={submitCancel}>
                <Field label="合同编号">
                  <input value={cancelEntrustNo} onChange={(e) => setCancelEntrustNo(e.target.value)} className={`${inputClass} font-mono-num`} placeholder="5963530617" required />
                </Field>
                <button type="submit" disabled={Boolean(busy) || !selectedAccountTradeable} className="flex w-full items-center justify-center gap-2 rounded-md border border-error/50 px-4 py-2.5 text-sm font-semibold text-error hover:bg-error/10 disabled:cursor-not-allowed disabled:opacity-60">
                  {busy === 'cancel' && <Loader2 className="size-4 animate-spin" />}
                  执行撤单
                </button>
              </form>
            </section>
          </div>

          <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-1 rounded-md bg-surface-container p-1">
                <TabButton active={workspaceTab === 'positions'} label="持仓" onClick={() => setWorkspaceTab('positions')} />
                <TabButton active={workspaceTab === 'orders'} label="委托" onClick={() => setWorkspaceTab('orders')} />
                <TabButton active={workspaceTab === 'trades'} label="成交" onClick={() => setWorkspaceTab('trades')} />
                <TabButton active={workspaceTab === 'logs'} label="日志" onClick={() => setWorkspaceTab('logs')} />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {(workspaceTab === 'orders' || workspaceTab === 'trades') && (
                  <div className="flex flex-wrap gap-1 rounded-md bg-surface-container p-1">
                    <TabButton active={scope === 'today'} label="当日" onClick={() => switchScope('today')} />
                    <TabButton active={scope === 'history'} label="历史" onClick={() => switchScope('history')} />
                  </div>
                )}
                <ActionButton label="刷新" icon={<RefreshCcw className="size-4" />} onClick={refreshWorkspace} />
              </div>
            </div>
            <div className="mb-3 rounded-md bg-surface-container px-3 py-2 text-xs text-on-surface-variant">
              {selectedAccount
                ? `当前账户：${selectedAccount.account_name}（${accountTypeLabel(selectedAccount.account_type)}）。${selectedAccount.account_type === 'live' ? '委托/成交从同花顺同步后保存。' : '委托/成交从本地持久化表读取。'}`
                : '未选择账户时，实盘查询跟随同花顺当前登录账户。'}
            </div>
            {workspaceTab === 'positions' && (
              <DataTable
                empty="暂无持仓数据"
                headers={['代码', '名称', '持仓', '可卖', '成本', '现价', '市值', '浮盈']}
                rows={positions.map((row) => [
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
            )}
            {workspaceTab === 'orders' && (
              <DataTable
                empty="暂无委托记录"
                headers={['合同编号', '代码', '名称', '方向', '价格', '数量', '成交', '状态', '时间']}
                rows={orders.map((row) => [
                  row.broker_order_id || row.order_id,
                  row.symbol,
                  row.name,
                  <SideText side={row.side} />,
                  money(row.price),
                  numberText(row.quantity),
                  numberText(row.filled_quantity),
                  row.status || '-',
                  row.submitted_at || '-',
                ])}
              />
            )}
            {workspaceTab === 'trades' && (
              <DataTable
                empty="暂无成交记录"
                headers={['成交编号', '合同编号', '代码', '名称', '方向', '价格', '数量', '金额', '时间']}
                rows={trades.map((row) => [
                  row.broker_trade_id || row.trade_id,
                  row.order_id,
                  row.symbol,
                  row.name,
                  <SideText side={row.side} />,
                  money(row.price),
                  numberText(row.quantity),
                  money(row.amount),
                  row.traded_at || '-',
                ])}
              />
            )}
            {workspaceTab === 'logs' && (
              <DataTable
                empty="暂无自动化日志"
                headers={['时间', '操作', '状态', '信息']}
                rows={logs.map((row) => [
                  row.created_at,
                  row.operation,
                  <span className={row.status === 'success' ? 'text-success' : 'text-warning'}>{row.status}</span>,
                  row.message,
                ])}
              />
            )}
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

function Notice({ busy, message, error }: { busy: string; message: string; error: string }) {
  return (
    <div className="rounded-md border border-outline bg-surface-container px-4 py-3 text-sm">
      {busy && <div className="flex items-center gap-2 text-primary"><Loader2 className="size-4 animate-spin" />{busy}中；如弹出验证码，请在桌面弹窗输入并确认。</div>}
      {message && !busy && <div className="text-success">{message}</div>}
      {error && <div className="text-error">{error}</div>}
    </div>
  )
}

function ActionButton({ label, icon, disabled, onClick }: { label: string; icon?: React.ReactNode; disabled?: boolean; onClick: () => void }) {
  return <button type="button" disabled={disabled} onClick={onClick} className="inline-flex items-center gap-2 rounded-md border border-outline bg-surface-container px-3 py-2 text-sm text-on-surface hover:bg-surface-container-highest disabled:cursor-not-allowed disabled:opacity-60">{icon}{label}</button>
}

function TabButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`rounded-sm px-3 py-2 text-sm ${active ? 'bg-primary/15 text-primary' : 'text-on-surface-variant hover:bg-surface-container-high'}`}>{label}</button>
}

function MetricCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return <div className="rounded-lg bg-surface-container-high p-4 shadow-card"><div className="mb-3 flex items-center justify-between text-on-surface-variant"><span className="text-xs">{label}</span>{icon}</div><div className="font-mono-num text-xl font-semibold text-on-surface">{value}</div></div>
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md bg-surface-container px-3 py-2"><div className="mb-1 text-xs text-on-surface-variant">{label}</div><div className="truncate font-mono-num text-sm text-on-surface">{value}</div></div>
}

function DataTable({ headers, rows, empty }: { headers: string[]; rows: React.ReactNode[][]; empty: string }) {
  if (!rows.length) return <div className="flex h-64 items-center justify-center rounded-md border border-outline-variant text-sm text-on-surface-variant">{empty}</div>
  return <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-sm"><thead><tr className="border-b border-outline text-xs text-on-surface-variant">{headers.map((h) => <th key={h} className="whitespace-nowrap px-3 py-2 text-left font-medium">{h}</th>)}</tr></thead><tbody className="divide-y divide-outline-variant/40">{rows.map((cells, i) => <tr key={i} className="hover:bg-surface-container-highest">{cells.map((cell, j) => <td key={j} className="whitespace-nowrap px-3 py-2 font-mono-num">{cell || '-'}</td>)}</tr>)}</tbody></table></div>
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
