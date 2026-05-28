import { AppLayout } from '@/common/components'
import request from '@/common/utils/request'
import { AlertTriangle, Loader2, Pencil, Plus, RefreshCcw, ShieldCheck, Star, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

type ApiResponse<T> = {
  success: boolean
  data: T
  message: string
}

type AccountBinding = {
  id: number
  binding_type: string
  client_path: string | null
  client_identity: string | null
  is_active: boolean
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
  meta_json: Record<string, unknown>
  bindings: AccountBinding[]
}

const apiTimeout = 240000
const inputClass =
  'h-10 w-full rounded-md border border-outline bg-surface-container px-3 text-sm text-on-surface outline-none transition-colors placeholder:text-on-surface-variant focus:border-primary'

export default function AccountManagement() {
  const [accounts, setAccounts] = useState<ManagedAccount[]>([])
  const [editingId, setEditingId] = useState<number | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState(emptyForm())
  const [pendingDelete, setPendingDelete] = useState<ManagedAccount | null>(null)

  const busyText = useMemo(
    () =>
      ({
        list: '刷新账户',
        create: '创建账户',
        update: '更新账户',
        delete: '删除账户',
        default: '设置默认账户',
        status: '识别当前账户',
      })[busy || ''] || '',
    [busy]
  )

  useEffect(() => {
    void refreshAccounts()
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

  async function refreshAccounts() {
    const data = await callApi<ManagedAccount[]>('list', () =>
      request.get('/account/accounts', { timeout: apiTimeout }) as Promise<ApiResponse<ManagedAccount[]>>
    )
    if (data) setAccounts(data.filter((account) => account.status !== 'archived'))
  }

  async function fillFromCurrentClient() {
    const data = await callApi<any>('status', () =>
      request.get('/account/automation/status', { timeout: apiTimeout }) as Promise<ApiResponse<any>>
    )
    const account = data?.account
    if (!account) return
    setForm((prev) => ({
      ...prev,
      account_name: account.account_name || prev.account_name,
      account_type: account.account_type === 'unknown' ? prev.account_type : account.account_type,
      broker_name: '同花顺',
      broker_account_no: account.capital_account || prev.broker_account_no,
      shareholder_account: account.shareholder_account || prev.shareholder_account,
      exchange: account.market || prev.exchange,
      binding_type: account.account_type === 'paper' ? 'mock' : 'desktop',
    }))
    await refreshAccounts()
  }

  function editAccount(account: ManagedAccount) {
    const binding = account.bindings?.[0]
    setEditingId(account.id)
    setForm({
      account_code: account.account_code || '',
      account_name: account.account_name || '',
      account_type: account.account_type,
      broker_name: account.broker_name || '',
      broker_account_no: account.broker_account_no || '',
      shareholder_account: account.shareholder_account || '',
      exchange: account.exchange || '',
      status: account.status,
      is_default: account.is_default,
      binding_type: binding?.binding_type || defaultBindingType(account.account_type),
      client_path: binding?.client_path || '',
      client_identity: binding?.client_identity || '',
      binding_active: binding?.is_active ?? true,
      initial_cash: String(account.meta_json?.initial_cash || ''),
      meta_json_text: JSON.stringify(account.meta_json || {}, null, 2),
    })
  }

  async function submitAccount(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    let metaJson: Record<string, unknown> | undefined
    if (form.meta_json_text.trim()) {
      try {
        metaJson = JSON.parse(form.meta_json_text)
      } catch {
        setError('账户扩展信息必须是合法 JSON')
        return
      }
    }
    const payload = {
      account_code: form.account_code.trim() || undefined,
      account_name: form.account_name.trim(),
      account_type: form.account_type,
      broker_name: form.broker_name.trim() || undefined,
      broker_account_no: form.broker_account_no.trim() || undefined,
      shareholder_account: form.shareholder_account.trim() || undefined,
      exchange: form.exchange.trim() || undefined,
      status: form.status,
      is_default: form.is_default,
      binding_type: form.binding_type,
      client_path: form.client_path.trim() || undefined,
      client_identity: form.client_identity.trim() || undefined,
      binding_active: form.binding_active,
      initial_cash: ['paper', 'backtest'].includes(form.account_type) && form.initial_cash.trim() ? form.initial_cash.trim() : undefined,
      meta_json: metaJson,
    }
    const data = await callApi<ManagedAccount>(editingId ? 'update' : 'create', () =>
      (editingId
        ? request.put(`/account/accounts/${editingId}`, payload, { timeout: apiTimeout })
        : request.post('/account/accounts', payload, { timeout: apiTimeout })) as Promise<ApiResponse<ManagedAccount>>
    )
    if (data) {
      setEditingId(null)
      setForm(emptyForm())
      await refreshAccounts()
    }
  }

  async function deleteAccount() {
    if (!pendingDelete) return
    const deletingId = pendingDelete.id
    const data = await callApi<ManagedAccount>('delete', () =>
      request.post(`/account/accounts/${deletingId}/archive`, {}, { timeout: apiTimeout }) as Promise<ApiResponse<ManagedAccount>>
    )
    if (data) {
      if (editingId === deletingId) {
        setEditingId(null)
        setForm(emptyForm())
      }
      setPendingDelete(null)
      await refreshAccounts()
    }
  }

  async function setDefaultAccount(id: number) {
    const data = await callApi<ManagedAccount>('default', () =>
      request.post(`/account/accounts/${id}/default`, {}, { timeout: apiTimeout }) as Promise<ApiResponse<ManagedAccount>>
    )
    if (data) await refreshAccounts()
  }

  return (
    <AppLayout>
      <div className="space-y-5">
        <Header
          title="账户管理"
          desc="维护实盘账户、模拟盘账户、回测账户的主档和交易端绑定关系。"
          actions={
            <>
              <ActionButton label="识别当前账户" icon={<ShieldCheck className="size-4" />} onClick={fillFromCurrentClient} />
              <ActionButton label="刷新账户" icon={<RefreshCcw className="size-4" />} onClick={refreshAccounts} />
            </>
          }
        />

        {(message || error || busy) && (
          <Notice busy={busyText} message={message} error={error} />
        )}

        <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
          <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold">{editingId ? '编辑账户' : '新增账户'}</h2>
              <ActionButton
                label="清空"
                icon={<Plus className="size-4" />}
                onClick={() => {
                  setEditingId(null)
                  setForm(emptyForm())
                }}
              />
            </div>
            <form className="space-y-3" onSubmit={submitAccount}>
              <div className="grid grid-cols-2 gap-3">
                <Field label="账户编码">
                  <input value={form.account_code} onChange={(e) => setForm({ ...form, account_code: e.target.value })} className={inputClass} placeholder="LIVE_THS_001" />
                </Field>
                <Field label="账户名称">
                  <input value={form.account_name} onChange={(e) => setForm({ ...form, account_name: e.target.value })} className={inputClass} placeholder="实盘主账户" required />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="账户类型">
                  <select
                    value={form.account_type}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        account_type: e.target.value as 'live' | 'paper' | 'backtest',
                        binding_type: defaultBindingType(e.target.value as 'live' | 'paper' | 'backtest'),
                      })
                    }
                    className={inputClass}
                  >
                    <option value="live">实盘</option>
                    <option value="paper">模拟盘</option>
                    <option value="backtest">回测盘</option>
                  </select>
                </Field>
                <Field label="状态">
                  <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as any })} className={inputClass}>
                    <option value="active">启用</option>
                    <option value="inactive">停用</option>
                    <option value="archived">归档</option>
                  </select>
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="券商/平台">
                  <input value={form.broker_name} onChange={(e) => setForm({ ...form, broker_name: e.target.value })} className={inputClass} placeholder="同花顺" />
                </Field>
                <Field label="交易市场">
                  <input value={form.exchange} onChange={(e) => setForm({ ...form, exchange: e.target.value })} className={inputClass} placeholder="SH/SZ/BJ" />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="资金账号">
                  <input value={form.broker_account_no} onChange={(e) => setForm({ ...form, broker_account_no: e.target.value })} className={inputClass} />
                </Field>
                <Field label="股东账号">
                  <input value={form.shareholder_account} onChange={(e) => setForm({ ...form, shareholder_account: e.target.value })} className={inputClass} />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="绑定类型">
                  <select value={form.binding_type} onChange={(e) => setForm({ ...form, binding_type: e.target.value })} className={inputClass}>
                    <option value="desktop">桌面自动化</option>
                    <option value="ths">同花顺</option>
                    <option value="mock">模拟适配器</option>
                    <option value="webapi">券商 API</option>
                    <option value="backtest">回测引擎</option>
                  </select>
                </Field>
                <Field label="客户端标识">
                  <input value={form.client_identity} onChange={(e) => setForm({ ...form, client_identity: e.target.value })} className={inputClass} placeholder="ths:LIVE_THS_001" />
                </Field>
              </div>
              <Field label="客户端路径">
                <input value={form.client_path} onChange={(e) => setForm({ ...form, client_path: e.target.value })} className={inputClass} placeholder="E:\\同花顺软件\\同花顺\\xiadan.exe" />
              </Field>
              {['paper', 'backtest'].includes(form.account_type) && (
                <Field label={form.account_type === 'backtest' ? '回测初始资金' : '模拟初始资金'}>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.initial_cash}
                    onChange={(e) => setForm({ ...form, initial_cash: e.target.value })}
                    className={`${inputClass} font-mono-num`}
                    placeholder="1000000"
                  />
                </Field>
              )}
              <div className="grid grid-cols-2 gap-3">
                <label className="flex items-center gap-2 rounded-md bg-surface-container px-3 py-2 text-sm text-on-surface-variant">
                  <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} className="size-4 accent-primary" />
                  默认账户
                </label>
                <label className="flex items-center gap-2 rounded-md bg-surface-container px-3 py-2 text-sm text-on-surface-variant">
                  <input type="checkbox" checked={form.binding_active} onChange={(e) => setForm({ ...form, binding_active: e.target.checked })} className="size-4 accent-primary" />
                  绑定启用
                </label>
              </div>
              <Field label="扩展信息 JSON">
                <textarea
                  value={form.meta_json_text}
                  onChange={(e) => setForm({ ...form, meta_json_text: e.target.value })}
                  className="min-h-20 w-full rounded-md border border-outline bg-surface-container px-3 py-2 text-sm text-on-surface outline-none placeholder:text-on-surface-variant focus:border-primary"
                  placeholder='{"tag":"main"}'
                />
              </Field>
              <button type="submit" disabled={Boolean(busy)} className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-on-primary disabled:cursor-not-allowed disabled:opacity-60">
                {busy === 'create' || busy === 'update' ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
                {editingId ? '保存修改' : '创建账户'}
              </button>
            </form>
          </section>

          <section className="rounded-lg bg-surface-container-high p-4 shadow-card">
            <h2 className="mb-4 text-sm font-semibold">账户列表</h2>
            <DataTable
              empty="暂无账户"
              headers={['编码', '名称', '类型', '状态', '默认', '绑定', '操作']}
              rows={accounts.map((row) => [
                row.account_code,
                row.account_name,
                accountTypeLabel(row.account_type),
                statusLabel(row.status),
                row.is_default ? <span className="text-warning">是</span> : '-',
                row.bindings?.[0]?.client_path || row.bindings?.[0]?.binding_type || '-',
                <div className="flex flex-wrap gap-2">
                  <SmallButton label="编辑" icon={<Pencil className="size-3" />} onClick={() => editAccount(row)} />
                  <SmallButton label="设默认" icon={<Star className="size-3" />} tone="warning" onClick={() => setDefaultAccount(row.id)} />
                  <SmallButton label="删除" icon={<Trash2 className="size-3" />} tone="error" onClick={() => setPendingDelete(row)} />
                </div>,
              ])}
            />
          </section>
        </div>

        {pendingDelete && (
          <ConfirmDeleteDialog
            account={pendingDelete}
            busy={busy === 'delete'}
            onCancel={() => setPendingDelete(null)}
            onConfirm={deleteAccount}
          />
        )}
      </div>
    </AppLayout>
  )
}

function emptyForm() {
  return {
    account_code: '',
    account_name: '',
    account_type: 'live' as 'live' | 'paper' | 'backtest',
    broker_name: '同花顺',
    broker_account_no: '',
    shareholder_account: '',
    exchange: '',
    status: 'active' as 'active' | 'inactive' | 'archived',
    is_default: true,
    binding_type: 'desktop',
    client_path: '',
    client_identity: '',
    binding_active: true,
    initial_cash: '',
    meta_json_text: '',
  }
}

function Header({ title, desc, actions }: { title: string; desc: string; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
      <div>
        <h1 className="text-xl font-semibold text-on-surface">{title}</h1>
        <p className="mt-1 text-sm text-on-surface-variant">{desc}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">{actions}</div>
    </div>
  )
}

function Notice({ busy, message, error }: { busy: string; message: string; error: string }) {
  return (
    <div className="rounded-md border border-outline bg-surface-container px-4 py-3 text-sm">
      {busy && (
        <div className="flex items-center gap-2 text-primary">
          <Loader2 className="size-4 animate-spin" />
          {busy}中
        </div>
      )}
      {message && !busy && <div className="text-success">{message}</div>}
      {error && <div className="text-error">{error}</div>}
    </div>
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

function ActionButton({ label, icon, onClick }: { label: string; icon?: React.ReactNode; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="inline-flex items-center gap-2 rounded-md border border-outline bg-surface-container px-3 py-2 text-sm text-on-surface hover:bg-surface-container-highest">
      {icon}
      {label}
    </button>
  )
}

function SmallButton({ label, icon, tone = 'primary', onClick }: { label: string; icon?: React.ReactNode; tone?: 'primary' | 'warning' | 'error'; onClick: () => void }) {
  const toneClass = tone === 'error' ? 'text-error hover:bg-error/10' : tone === 'warning' ? 'text-warning hover:bg-warning/10' : 'text-primary hover:bg-primary/10'
  return (
    <button type="button" onClick={onClick} className={`inline-flex items-center gap-1 rounded-sm px-2 py-1 text-xs ${toneClass}`}>
      {icon}
      {label}
    </button>
  )
}

function ConfirmDeleteDialog({
  account,
  busy,
  onCancel,
  onConfirm,
}: {
  account: ManagedAccount
  busy: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 px-4">
      <div className="w-full max-w-md rounded-lg border border-error/40 bg-surface-container-high p-5 shadow-card">
        <div className="mb-4 flex items-start gap-3">
          <div className="rounded-md bg-error/10 p-2 text-error">
            <AlertTriangle className="size-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-on-surface">确认删除账户</h3>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">
              删除后账户会从账户管理和交易选择中隐藏，历史交易、成交、资金快照仍会保留用于复盘。
            </p>
          </div>
        </div>
        <div className="rounded-md bg-surface-container px-3 py-2 text-sm">
          <div className="font-semibold text-on-surface">{account.account_name}</div>
          <div className="mt-1 font-mono-num text-xs text-on-surface-variant">{account.account_code}</div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" disabled={busy} onClick={onCancel} className="rounded-md border border-outline px-4 py-2 text-sm text-on-surface hover:bg-surface-container-highest disabled:cursor-not-allowed disabled:opacity-60">
            取消
          </button>
          <button type="button" disabled={busy} onClick={onConfirm} className="inline-flex items-center gap-2 rounded-md bg-error px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">
            {busy && <Loader2 className="size-4 animate-spin" />}
            确认删除
          </button>
        </div>
      </div>
    </div>
  )
}

function DataTable({ headers, rows, empty }: { headers: string[]; rows: React.ReactNode[][]; empty: string }) {
  if (!rows.length) {
    return <div className="flex h-64 items-center justify-center rounded-md border border-outline-variant text-sm text-on-surface-variant">{empty}</div>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-sm">
        <thead>
          <tr className="border-b border-outline text-xs text-on-surface-variant">
            {headers.map((header) => (
              <th key={header} className="whitespace-nowrap px-3 py-2 text-left font-medium">{header}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/40">
          {rows.map((cells, index) => (
            <tr key={index} className="hover:bg-surface-container-highest">
              {cells.map((cell, cellIndex) => (
                <td key={cellIndex} className="whitespace-nowrap px-3 py-2 font-mono-num">{cell || '-'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function accountTypeLabel(value: string) {
  if (value === 'live') return '实盘'
  if (value === 'paper') return '模拟盘'
  if (value === 'backtest') return '回测盘'
  return value || '-'
}

function statusLabel(value: string) {
  if (value === 'active') return '启用'
  if (value === 'inactive') return '停用'
  if (value === 'archived') return '归档'
  return value || '-'
}

function defaultBindingType(value: 'live' | 'paper' | 'backtest') {
  if (value === 'live') return 'desktop'
  if (value === 'backtest') return 'backtest'
  return 'mock'
}
