import { NavLink } from 'react-router-dom'
import { Activity, Video, BookOpen, Library } from 'lucide-react'

const NAV = [
  { to: '/',        icon: Activity, label: 'Home',    end: true },
  { to: '/analyze', icon: Video,    label: 'Analyze', end: false },
  { to: '/record',  icon: BookOpen, label: 'Record',  end: false },
  { to: '/library', icon: Library,  label: 'Library', end: false },
]

export default function Layout({ children }) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="w-56 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Activity className="w-4.5 h-4.5 text-white" strokeWidth={2.5} />
            </div>
            <div className="leading-tight">
              <p className="text-white font-bold text-sm">AI Fitness</p>
              <p className="text-slate-500 text-xs">Coach  v0.1</p>
            </div>
          </div>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/25'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-slate-800">
          <p className="text-slate-600 text-xs leading-relaxed">
            MediaPipe · FastDTW · FastAPI
          </p>
        </div>
      </aside>

      {/* ── Main content ────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
