import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Activity,
  UserCog,
  ArrowLeftRight,
  Brain,
  MonitorPlay,
  ChartBar,
  History,
  Search,
  Bell,
  CandlestickChart,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/common/utils'

const navItems = [
  { href: '/', label: '首页', icon: LayoutDashboard },
  { href: '/api-data', label: '行情数据', icon: Activity },
  { href: '/account/manage', label: '账户管理', icon: UserCog },
  { href: '/account/trading', label: '交易界面', icon: ArrowLeftRight },
  { href: '/strategies', label: '策略管理', icon: Brain },
  { href: '/execution', label: '执行监控', icon: MonitorPlay },
  { href: '/review', label: '复盘分析', icon: ChartBar },
  { href: '/replay', label: '历史回放', icon: History },
] as const

export function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className={cn(
          'shrink-0 bg-background flex flex-col border-r border-outline-variant/20 transition-all duration-200',
          collapsed ? 'w-16' : 'w-56'
        )}
      >
        {/* Logo */}
        <div className="h-14 flex items-center gap-2.5 px-5 border-b border-outline-variant/20">
          <CandlestickChart className="w-5 h-5 text-primary shrink-0" />
          {!collapsed && (
            <span className="font-bold text-sm tracking-wide">QuantFlow</span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 px-3 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const isActive =
              item.href === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.href)
            const Icon = item.icon

            return (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            )
          })}
        </nav>

        {/* Bottom */}
        <div className="p-3 border-t border-outline-variant/20">
          <div className="flex items-center gap-2 px-2 py-1.5">
            <div className="w-7 h-7 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs font-bold shrink-0">
              初
            </div>
            {!collapsed && (
              <span className="text-sm text-on-surface-variant">小初</span>
            )}
          </div>
        </div>
      </aside>

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-14 shrink-0 bg-surface flex items-center justify-between px-6 border-b border-outline-variant/20">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-1.5 rounded-md hover:bg-surface-container-high transition-colors text-on-surface-variant"
            >
              {collapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronLeft className="w-4 h-4" />
              )}
            </button>
          </div>
          <div className="flex items-center gap-4">
            {/* 搜索 */}
            <div className="flex items-center gap-2 bg-surface-container rounded-md px-3 py-1.5 text-sm text-on-surface-variant">
              <Search className="w-3.5 h-3.5" />
              <span>搜索...</span>
            </div>
            {/* 连接状态 */}
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
              <span className="text-xs text-on-surface-variant">已连接</span>
            </div>
            {/* 通知 */}
            <button className="relative p-1.5 rounded-md hover:bg-surface-container-high transition-colors">
              <Bell className="w-4 h-4 text-on-surface-variant" />
              <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-error text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                3
              </span>
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 min-w-0 overflow-y-auto bg-background p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
