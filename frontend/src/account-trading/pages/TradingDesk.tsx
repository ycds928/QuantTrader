import { AppLayout } from '@/common/components'
import request from '@/common/utils/request'
import { Activity, Ban, ClipboardList, Loader2, RefreshCcw, ShieldCheck, Wallet } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

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
type AccountSnapshot = {
  balance: Balance
  positions: Position[]
  orders: OrderRow[]
  trades: TradeRow[]
}
type PlaceOrderResult = {
  status?: string
  reason?: string
  order?: Partial<OrderRow>
  trade?: Partial<TradeRow> | null
}
type SecurityLookup = {
  query: string
  symbol: string
  name: string
  exchange: string
  last_price: string
  bid_price_1: string
  bid_volume_1: number
  ask_price_1: string
  ask_volume_1: number
  bid_levels?: QuoteLevel[]
  ask_levels?: QuoteLevel[]
  default_price: string
  default_price_source: string
  source: string
  resolved_at: string
}
type QuoteLevel = {
  level: number
  price: string
  volume: number
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
  selected_engine?: string
  desktop_required?: boolean
  message?: string
  window_title?: string
  window_rect?: string
  selected_account?: {
    id: number
    account_code: string
    account_name: string
    account_type: 'live' | 'paper' | 'backtest'
    account_type_label: string
  }
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
  const [selectedOrderKeys, setSelectedOrderKeys] = useState<string[]>([])
  const [trades, setTrades] = useState<TradeRow[]>([])
  const [logs, setLogs] = useState<AutomationLog[]>([])
  const [status, setStatus] = useState<AutomationStatus | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [waitCaptcha, setWaitCaptcha] = useState(true)
  const [securityQuery, setSecurityQuery] = useState('301183')
  const [securityLookup, setSecurityLookup] = useState<SecurityLookup | null>(null)
  const [securityLookupBusy, setSecurityLookupBusy] = useState(false)
  const priceTouchedRef = useRef(false)
  const [orderForm, setOrderForm] = useState({
    side: 'buy' as 'buy' | 'sell',
    symbol: '301183',
    price: '',
    quantity: '100',
    remark: '',
  })

  const busyText = useMemo(
    () =>
      ({
        status: '检查连接',
        connect: '连接交易端',
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
  const selectedAccountTradeable = !selectedAccount || ['live', 'paper', 'backtest'].includes(selectedAccount.account_type)
  const selectedEngine = selectedAccount ? engineLabel(selectedAccount.account_type) : '桌面实盘引擎'
  const cancellableOrders = orders.filter((row) => canCancelOrder(row, selectedAccount?.account_type, scope))
  const selectedCancelableOrders = cancellableOrders.filter((row) => selectedOrderKeys.includes(orderKey(row)))
  const accountInfo = selectedAccount
    ? {
        name: selectedAccount.account_name,
        code: selectedAccount.account_code,
        capital: selectedAccount.broker_account_no || selectedAccount.account_code,
        shareholder: selectedAccount.shareholder_account || '-',
        market: selectedAccount.exchange || '-',
      }
    : {
        name: status?.account?.account_name || '-',
        code: '-',
        capital: status?.account?.capital_account || '-',
        shareholder: status?.account?.shareholder_account || '-',
        market: status?.account?.market || '-',
      }

  useEffect(() => {
    void refreshAccounts()
    void refreshLogs(false)
  }, [])

  useEffect(() => {
    const keyword = securityQuery.trim()
    if (keyword.length < 2) {
      setSecurityLookup(null)
      return
    }
    let canceled = false
    const timer = window.setTimeout(async () => {
      setSecurityLookupBusy(true)
      try {
        const response = await request.get('/api-data/security-lookup', {
          params: { keyword, side: orderForm.side },
          timeout: 10000,
        }) as ApiResponse<SecurityLookup>
        if (canceled) return
        const data = response.data
        setSecurityLookup(data?.symbol ? data : null)
        if (data?.symbol) {
          setOrderForm((prev) => ({
            ...prev,
            symbol: data.symbol,
            price: priceTouchedRef.current ? prev.price : data.default_price || prev.price,
          }))
        }
      } catch {
        if (!canceled) setSecurityLookup(null)
      } finally {
        if (!canceled) setSecurityLookupBusy(false)
      }
    }, 450)
    return () => {
      canceled = true
      window.clearTimeout(timer)
    }
  }, [securityQuery, orderForm.side])

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

  async function connectTradingClient() {
    const data = await callApi<AutomationStatus>('connect', () =>
      request.post(
        '/account/automation/connect',
        { account_id: selectedAccountId || undefined },
        { timeout: apiTimeout }
      ) as Promise<ApiResponse<AutomationStatus>>
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
      const nextAccountId = selectedAccountId || defaultAccount?.id || firstActive?.id || null
      setSelectedAccountId(nextAccountId)
      if (nextAccountId) await loadAccountSnapshot(nextAccountId)
    }
  }

  async function loadAccountSnapshot(accountId = selectedAccountId, nextScope = scope) {
    if (!accountId) return
    const data = await callApi<AccountSnapshot>('snapshot', () =>
      request.get('/account/snapshot', {
        params: { account_id: accountId, scope: nextScope },
        timeout: apiTimeout,
      }) as Promise<ApiResponse<AccountSnapshot>>
    )
    if (data) {
      setBalance(data.balance)
      setPositions(data.positions)
      setOrders(data.orders)
      setSelectedOrderKeys([])
      setTrades(data.trades)
    }
  }

  async function syncAccount() {
    if (selectedAccount && !selectedAccountTradeable) {
      setError('当前选择的账户暂不支持交易台同步。')
      return
    }
    const data = await callApi<AccountSnapshot>('sync', () =>
      request.post(
        '/account/sync',
        {
          account_id: selectedAccountId || undefined,
          wait_manual_captcha: waitCaptcha,
          manual_captcha_timeout: 180,
        },
        { timeout: apiTimeout }
      ) as Promise<ApiResponse<AccountSnapshot>>
    )
    if (data) {
      setBalance(data.balance)
      setPositions(data.positions)
      setOrders(data.orders || [])
      setSelectedOrderKeys([])
      setTrades(data.trades || [])
      setScope('today')
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
    if (data) {
      setOrders(data)
      setSelectedOrderKeys((current) =>
        current.filter((key) => data.some((row) => orderKey(row) === key && canCancelOrder(row, selectedAccount?.account_type, nextScope)))
      )
    }
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
    const mode = selectedAccount?.account_type || 'live'
    if (!orderForm.symbol.trim()) {
      setError('请先输入证券代码或名称，并等待系统识别证券信息。')
      return
    }
    const data = await callApi<PlaceOrderResult>('order', () =>
      request.post(
        '/account/order',
        {
          symbol: orderForm.symbol.trim(),
          name: securityLookup?.symbol === orderForm.symbol.trim() ? securityLookup.name : undefined,
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
      ) as Promise<ApiResponse<PlaceOrderResult>>
    )
    if (data) {
      const notice = orderResultNotice(data)
      const normalized = normalizeOrderStatus(data.status || data.order?.status || '')
      await syncAccount()
      setWorkspaceTab('orders')
      setScope('today')
      if (['rejected', 'failed'].includes(normalized)) {
        setError(notice)
        setMessage('')
      } else {
        setMessage(notice)
        setError('')
      }
    }
  }

  async function refreshWorkspace() {
    if (workspaceTab === 'positions') await syncAccount()
    if (workspaceTab === 'orders') await refreshOrders()
    if (workspaceTab === 'trades') await refreshTrades()
    if (workspaceTab === 'logs') await refreshLogs()
  }

  async function switchScope(nextScope: Scope) {
    setScope(nextScope)
    if (workspaceTab === 'orders' || workspaceTab === 'trades') await loadAccountSnapshot(selectedAccountId, nextScope)
  }

  async function switchAccount(value: string) {
    const nextAccountId = value ? Number(value) : null
    setSelectedAccountId(nextAccountId)
    setBalance(null)
    setPositions([])
    setOrders([])
    setSelectedOrderKeys([])
    setTrades([])
    setMessage('')
    setError('')
    if (nextAccountId) await loadAccountSnapshot(nextAccountId)
  }

  async function cancelOrder(row: OrderRow) {
    const entrustNo = (row.broker_order_id || row.order_id || '').trim()
    if (!entrustNo) {
      setError('当前委托记录缺少合同编号，无法撤单。')
      return
    }
    if (selectedAccount && selectedAccount.account_type !== 'live') {
      setError('当前账户引擎暂不支持在交易台撤单。')
      return
    }
    const confirmed = window.confirm(`确认撤销合同编号 ${entrustNo} 的委托吗？`)
    if (!confirmed) return
    const data = await callApi<Record<string, unknown>>('cancel', () =>
      request.post(
        `/account/order/${encodeURIComponent(entrustNo)}/cancel`,
        {
          account_id: selectedAccountId || undefined,
          wait_manual_captcha: waitCaptcha,
          manual_captcha_timeout: 180,
        },
        { timeout: apiTimeout }
      ) as Promise<ApiResponse<Record<string, unknown>>>
    )
    if (data) {
      setMessage(`已提交撤单请求：合同编号 ${entrustNo}。请以同步后的当日委托状态为准。`)
      await refreshOrders('today')
      await refreshTrades('today')
      await refreshLogs(false)
    }
  }

  async function cancelSelectedOrders() {
    if (!selectedCancelableOrders.length) {
      setError('请先勾选可以撤单的当日委托记录。')
      return
    }
    const entrustNos = selectedCancelableOrders.map((row) => row.broker_order_id || row.order_id).filter(Boolean)
    const confirmed = window.confirm(`确认撤销已选中的 ${entrustNos.length} 笔委托吗？\n${entrustNos.join('、')}`)
    if (!confirmed) return
    for (const entrustNo of entrustNos) {
      await callApi<Record<string, unknown>>('cancel', () =>
        request.post(
          `/account/order/${encodeURIComponent(entrustNo)}/cancel`,
          {
            account_id: selectedAccountId || undefined,
            wait_manual_captcha: waitCaptcha,
            manual_captcha_timeout: 180,
          },
          { timeout: apiTimeout }
        ) as Promise<ApiResponse<Record<string, unknown>>>
      )
    }
    setMessage(`已提交 ${entrustNos.length} 笔撤单请求。请以同步后的当日委托状态为准。`)
    setSelectedOrderKeys([])
    await refreshOrders('today')
    await refreshTrades('today')
    await refreshLogs(false)
  }

  async function cancelAllOrders() {
    if (selectedAccount && selectedAccount.account_type !== 'live') {
      setError('当前账户引擎暂不支持在交易台撤单。')
      return
    }
    const confirmText = window.prompt('全部撤销会撤掉当前实盘账户所有可撤委托。请输入“全部撤销”确认。')
    if (confirmText !== '全部撤销') return
    const data = await callApi<Record<string, unknown>>('cancel', () =>
      request.post(
        '/account/orders/cancel-all',
        {
          account_id: selectedAccountId || undefined,
          wait_manual_captcha: waitCaptcha,
          manual_captcha_timeout: 180,
        },
        { timeout: apiTimeout }
      ) as Promise<ApiResponse<Record<string, unknown>>>
    )
    if (data) {
      setMessage('已提交全部撤单请求。请以同步后的当日委托状态为准。')
      setSelectedOrderKeys([])
      await refreshOrders('today')
      await refreshTrades('today')
      await refreshLogs(false)
    }
  }

  function toggleOrderSelection(row: OrderRow, checked: boolean) {
    const key = orderKey(row)
    setSelectedOrderKeys((current) => checked ? Array.from(new Set([...current, key])) : current.filter((item) => item !== key))
  }

  return (
    <AppLayout>
      <div className="space-y-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-on-surface">交易界面</h1>
            <p className="mt-1 text-sm text-on-surface-variant">根据账户类型自动选择桌面实盘引擎、模拟交易引擎或回测交易引擎。</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 rounded-md bg-surface-container px-3 py-2 text-sm text-on-surface-variant">
              <input type="checkbox" checked={waitCaptcha} onChange={(e) => setWaitCaptcha(e.target.checked)} className="size-4 accent-primary" />
              验证码人工等待
            </label>
            <ActionButton label="连接" icon={<ShieldCheck className="size-4" />} onClick={connectTradingClient} />
            <ActionButton label="同步" icon={<RefreshCcw className="size-4" />} onClick={syncAccount} disabled={!selectedAccountTradeable} />
          </div>
        </div>

        {(message || error || busy) && <Notice busy={busyText} message={message} error={error} />}

        <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">交易账户</h2>
            <span className={`rounded-sm px-2 py-1 text-xs font-medium ${selectedAccount?.account_type === 'live' ? 'bg-error/15 text-error' : 'bg-primary/15 text-primary'}`}>
              {selectedAccount ? accountTypeLabel(selectedAccount.account_type) : status?.account?.account_type_label || '未知'}
            </span>
          </div>
          <div className="mb-3 grid gap-3 text-sm md:grid-cols-[minmax(220px,360px)_1fr]">
            <label className="block">
              <span className="mb-1 block text-xs text-on-surface-variant">选择账户</span>
              <select
                value={selectedAccountId ?? ''}
                onChange={(event) => void switchAccount(event.target.value)}
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
                ? `已选择：${selectedAccount.account_name}（${accountTypeLabel(selectedAccount.account_type)}）。当前使用${selectedEngine}。`
                : '未选择账户时，交易操作跟随同花顺当前登录账户。'}
              {status?.selected_account && status.account ? (
                <span className="mt-1 block">
                  桌面识别：{status.account.account_name || '-'} / {status.account.account_type_label || '未知'}，仅用于核对当前同花顺登录状态。
                </span>
              ) : null}
            </div>
          </div>
          <div className="grid gap-3 text-sm md:grid-cols-4">
            <InfoBlock label="账户名称" value={accountInfo.name} />
            <InfoBlock label="账户编码" value={accountInfo.code} />
            <InfoBlock label="资金账户" value={accountInfo.capital} />
            <InfoBlock label="交易市场" value={accountInfo.market} />
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
                <h2 className="text-sm font-semibold">交易委托</h2>
                <span className="rounded-sm bg-primary/10 px-2 py-1 text-xs text-primary">{selectedEngine}</span>
              </div>
              <form className="space-y-3" onSubmit={submitOrder}>
                <div className="grid grid-cols-2 gap-2 rounded-md bg-surface-container p-1">
                  {(['buy', 'sell'] as const).map((side) => (
                    <button
                      key={side}
                      type="button"
                      disabled={!selectedAccountTradeable}
                      onClick={() => {
                        priceTouchedRef.current = false
                        setOrderForm((prev) => ({
                          ...prev,
                          side,
                          price: securityLookup
                            ? side === 'buy'
                              ? securityLookup.ask_price_1 || securityLookup.last_price || prev.price
                              : securityLookup.bid_price_1 || securityLookup.last_price || prev.price
                            : prev.price,
                        }))
                      }}
                      className={`rounded-sm px-3 py-2 text-sm font-medium ${orderForm.side === side ? (side === 'buy' ? 'bg-up/15 text-up' : 'bg-down/15 text-down') : 'text-on-surface-variant hover:bg-surface-container-high'}`}
                    >
                      {side === 'buy' ? '买入' : '卖出'}
                    </button>
                  ))}
                </div>
                <Field label="证券代码/名称">
                  <input
                    value={securityQuery}
                    onChange={(e) => {
                      priceTouchedRef.current = false
                      setSecurityQuery(e.target.value)
                      setOrderForm((prev) => ({ ...prev, symbol: '', price: '' }))
                    }}
                    className={inputClass}
                    placeholder="301183 或 东田微"
                    required
                  />
                </Field>
                <SecurityQuotePanel lookup={securityLookup} loading={securityLookupBusy} side={orderForm.side} />
                <div className="grid grid-cols-2 gap-3">
                  <Field label="委托价格">
                    <input
                      value={orderForm.price}
                      onChange={(e) => {
                        priceTouchedRef.current = true
                        setOrderForm({ ...orderForm, price: e.target.value })
                      }}
                      className={`${inputClass} font-mono-num`}
                      placeholder="自动带出买一/卖一，可手动修改"
                      required
                    />
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

            <section className="rounded-lg bg-surface-container-high p-4 text-sm text-on-surface-variant shadow-card">
              <h2 className="mb-2 text-sm font-semibold text-on-surface">撤单</h2>
              <p>撤单入口已放到“委托”列表。刷新当日委托后，在对应记录右侧点击撤单即可。</p>
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
                {workspaceTab === 'orders' && scope === 'today' && selectedAccount?.account_type === 'live' && (
                  <>
                    <ActionButton
                      label={`撤销已选${selectedCancelableOrders.length ? `(${selectedCancelableOrders.length})` : ''}`}
                      icon={<Ban className="size-4" />}
                      onClick={cancelSelectedOrders}
                      disabled={!selectedCancelableOrders.length || Boolean(busy)}
                    />
                    <ActionButton
                      label="全部撤销"
                      icon={<Ban className="size-4" />}
                      onClick={cancelAllOrders}
                      disabled={!cancellableOrders.length || Boolean(busy)}
                    />
                  </>
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
                headers={['选择', '合同编号', '代码', '名称', '方向', '价格', '数量', '成交', '状态', '时间', '操作']}
                rows={orders.map((row) => [
                  <input
                    type="checkbox"
                    checked={selectedOrderKeys.includes(orderKey(row))}
                    disabled={!canCancelOrder(row, selectedAccount?.account_type, scope) || Boolean(busy)}
                    onChange={(event) => toggleOrderSelection(row, event.target.checked)}
                    className="size-4 accent-primary disabled:cursor-not-allowed disabled:opacity-40"
                  />,
                  row.broker_order_id || row.order_id,
                  row.symbol,
                  row.name,
                  <SideText side={row.side} />,
                  money(row.price),
                  numberText(row.quantity),
                  numberText(row.filled_quantity),
                  <OrderStatusText status={row.status} />,
                  row.submitted_at || '-',
                  <button
                    type="button"
                    disabled={!canCancelOrder(row, selectedAccount?.account_type, scope) || Boolean(busy)}
                    onClick={() => cancelOrder(row)}
                    className="inline-flex items-center gap-1 rounded-sm border border-error/50 px-2 py-1 text-xs font-medium text-error hover:bg-error/10 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {busy === 'cancel' ? <Loader2 className="size-3 animate-spin" /> : <Ban className="size-3" />}
                    撤单
                  </button>,
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

function SecurityQuotePanel({ lookup, loading, side }: { lookup: SecurityLookup | null; loading: boolean; side: 'buy' | 'sell' }) {
  if (loading) {
    return (
      <div className="rounded-md border border-outline bg-surface-container px-3 py-2 text-xs text-on-surface-variant">
        <span className="inline-flex items-center gap-2"><Loader2 className="size-3 animate-spin" />正在识别证券和行情</span>
      </div>
    )
  }
  if (!lookup) {
    return (
      <div className="rounded-md border border-outline bg-surface-container px-3 py-2 text-xs text-on-surface-variant">
        输入证券代码或名称后自动带出行情。买入默认卖一价，卖出默认买一价。
      </div>
    )
  }
  const defaultLabel = side === 'buy' ? '买入参考卖一' : '卖出参考买一'
  return (
    <div className="rounded-md border border-outline bg-surface-container px-3 py-2 text-xs">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="font-medium text-on-surface">
          {lookup.name || '-'} <span className="font-mono-num text-on-surface-variant">{lookup.symbol}</span>
          {lookup.exchange ? <span className="ml-2 rounded-sm bg-primary/10 px-1.5 py-0.5 text-primary">{lookup.exchange}</span> : null}
        </div>
        <div className="font-mono-num text-on-surface-variant">{lookup.resolved_at || ''}</div>
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <QuoteItem label="最新价" value={priceText(lookup.last_price)} />
        <QuoteItem label="买一" value={priceText(lookup.bid_price_1)} extra={lotText(lookup.bid_volume_1)} className="text-up" />
        <QuoteItem label="卖一" value={priceText(lookup.ask_price_1)} extra={lotText(lookup.ask_volume_1)} className="text-down" />
        <QuoteItem label={defaultLabel} value={priceText(lookup.default_price)} className="text-primary" />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <OrderBookSide title="买盘" levels={lookup.bid_levels || []} tone="bid" />
        <OrderBookSide title="卖盘" levels={lookup.ask_levels || []} tone="ask" />
      </div>
    </div>
  )
}

function OrderBookSide({ title, levels, tone }: { title: string; levels: QuoteLevel[]; tone: 'bid' | 'ask' }) {
  const className = tone === 'bid' ? 'text-up' : 'text-down'
  return (
    <div className="rounded-sm bg-surface-container-high px-2 py-2">
      <div className="mb-1 text-on-surface-variant">{title}</div>
      <div className="space-y-1">
        {levels.length ? levels.map((level) => (
          <div key={`${title}-${level.level}`} className="grid grid-cols-[44px_1fr_1fr] gap-2 font-mono-num">
            <span className="text-on-surface-variant">{tone === 'bid' ? '买' : '卖'}{level.level}</span>
            <span className={className}>{priceText(level.price)}</span>
            <span className="text-right text-on-surface-variant">{lotText(level.volume)}</span>
          </div>
        )) : <div className="text-on-surface-variant">暂无盘口</div>}
      </div>
    </div>
  )
}

function QuoteItem({ label, value, extra, className = '' }: { label: string; value: string; extra?: string; className?: string }) {
  return (
    <div>
      <div className="text-on-surface-variant">{label}</div>
      <div className={`font-mono-num text-sm font-medium ${className}`}>{value}</div>
      {extra ? <div className="font-mono-num text-on-surface-variant">{extra}</div> : null}
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

function priceText(value?: string | number) {
  const num = Number(value ?? 0)
  if (!Number.isFinite(num) || num <= 0) return '-'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

function lotText(value?: number) {
  const num = Number(value ?? 0)
  if (!Number.isFinite(num) || num <= 0) return ''
  return `${num.toLocaleString('zh-CN')} 手`
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

function OrderStatusText({ status }: { status: string }) {
  const label = orderStatusLabel(status)
  const normalized = normalizeOrderStatus(status)
  const className = ['filled'].includes(normalized)
    ? 'text-success'
    : ['rejected', 'failed', 'canceled', 'expired'].includes(normalized)
      ? 'text-error'
      : ['partial_filled', 'partial_canceled', 'partial_expired', 'cancel_pending'].includes(normalized)
        ? 'text-warning'
        : 'text-primary'
  return <span className={className}>{label}</span>
}

function orderResultNotice(result: PlaceOrderResult) {
  const order = result.order || {}
  const trade = result.trade || null
  const status = normalizeOrderStatus(result.status || order.status || '')
  const side = order.side ? (order.side === 'buy' ? '买入' : order.side === 'sell' ? '卖出' : order.side) : '委托'
  const symbolText = [order.name, order.symbol].filter(Boolean).join(' / ') || '证券'
  const orderNo = order.broker_order_id || order.order_id || '-'
  const quantity = Number(order.quantity || 0)
  const orderPrice = priceText(order.price)
  if (status === 'filled') {
    return `${symbolText} ${side}已全部成交，合同编号 ${orderNo}，委托价 ${orderPrice}，成交价 ${priceText(trade?.price || order.avg_fill_price)}，数量 ${numberText(quantity)}。`
  }
  if (status === 'partial_filled') {
    return `${symbolText} ${side}已部分成交，合同编号 ${orderNo}，委托价 ${orderPrice}，已成交 ${numberText(Number(order.filled_quantity || 0))} / ${numberText(quantity)}。`
  }
  if (status === 'submitted' || status === 'accepted') {
    return `${symbolText} ${side}委托已提交未成交，合同编号 ${orderNo}，委托价 ${orderPrice}，数量 ${numberText(quantity)}。已切换到“委托”列表，请不要重复提交同一笔。`
  }
  if (status === 'rejected') {
    return `${symbolText} ${side}委托被拒绝：${result.reason || '不满足交易条件'}。`
  }
  return `${symbolText} ${side}委托状态：${orderStatusLabel(status)}，合同编号 ${orderNo}。${result.reason || ''}`
}

function canCancelOrder(row: OrderRow, accountType?: string, scope?: Scope) {
  if (accountType && accountType !== 'live') return false
  if (scope !== 'today') return false
  if (!(row.broker_order_id || row.order_id)) return false
  return ['submitted', 'accepted', 'partial_filled', 'partial_canceled'].includes(normalizeOrderStatus(row.status))
}

function orderKey(row: OrderRow) {
  return row.broker_order_id || row.order_id || `${row.symbol}-${row.submitted_at}-${row.price}-${row.quantity}`
}

function normalizeOrderStatus(status: string) {
  const value = String(status || 'submitted').toLowerCase()
  if (['全部撤单', '已撤', 'canceled', 'cancelled'].some((item) => value.includes(item.toLowerCase()))) return 'canceled'
  if (['部分撤单', '部撤', 'partial_canceled'].some((item) => value.includes(item.toLowerCase()))) return 'partial_canceled'
  if (['全部成交', '已成', 'filled'].some((item) => value.includes(item.toLowerCase()))) return 'filled'
  if (['部分成交', '部成', 'partial_filled'].some((item) => value.includes(item.toLowerCase()))) return 'partial_filled'
  if (['撤单中', 'cancel_pending'].some((item) => value.includes(item.toLowerCase()))) return 'cancel_pending'
  if (['已失效', '失效', 'expired'].some((item) => value.includes(item.toLowerCase()))) return 'expired'
  if (['部分失效', 'partial_expired'].some((item) => value.includes(item.toLowerCase()))) return 'partial_expired'
  if (['废单', 'rejected'].some((item) => value.includes(item.toLowerCase()))) return 'rejected'
  if (['失败', 'failed'].some((item) => value.includes(item.toLowerCase()))) return 'failed'
  if (value.includes('accepted')) return 'accepted'
  if (['已提交未成交', '未成交', '已报', 'submitted', 'created'].some((item) => value.includes(item.toLowerCase()))) return 'submitted'
  return value || 'submitted'
}

function orderStatusLabel(status: string) {
  const normalized = normalizeOrderStatus(status)
  const labels: Record<string, string> = {
    submitted: '已提交未成交',
    accepted: '已提交未成交',
    partial_filled: '部分成交',
    filled: '全部成交',
    partial_canceled: '部分撤单',
    canceled: '全部撤单',
    cancel_pending: '撤单中',
    expired: '已失效',
    partial_expired: '部分成交后失效',
    rejected: '废单',
    failed: '失败',
  }
  return labels[normalized] || status || '已提交未成交'
}

function accountTypeLabel(value: string) {
  if (value === 'live') return '实盘'
  if (value === 'paper') return '模拟盘'
  if (value === 'backtest') return '回测盘'
  return value || '-'
}

function engineLabel(value: string) {
  if (value === 'live') return '桌面实盘引擎'
  if (value === 'paper') return '模拟交易引擎'
  if (value === 'backtest') return '回测交易引擎'
  return '未知交易引擎'
}
