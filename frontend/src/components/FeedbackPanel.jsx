import { AlertTriangle, Info, CheckCircle } from 'lucide-react'

const SEV = {
  critical: {
    Icon:   AlertTriangle,
    label:  'Critical',
    text:   'text-red-400',
    bg:     'bg-red-500/8',
    border: 'border-red-500/25',
    badge:  'bg-red-500/15 text-red-400',
  },
  technical: {
    Icon:   Info,
    label:  'Technical',
    text:   'text-yellow-400',
    bg:     'bg-yellow-500/8',
    border: 'border-yellow-500/25',
    badge:  'bg-yellow-500/15 text-yellow-400',
  },
}

export default function FeedbackPanel({ feedback }) {
  const { items = [], summary } = feedback

  if (!items.length) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/25 rounded-xl">
          <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
          <div>
            <p className="font-semibold text-green-400 text-sm">No significant errors detected</p>
            <p className="text-slate-400 text-sm">Your technique is on point!</p>
          </div>
        </div>
        {summary && (
          <div className="p-4 bg-slate-800/60 rounded-xl border border-slate-700">
            <p className="text-slate-300 text-sm italic leading-relaxed">{summary}</p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {items.map((item, i) => {
        const cfg = SEV[item.severity] ?? SEV.technical
        const { Icon } = cfg
        return (
          <div key={i} className={`p-4 rounded-xl border ${cfg.bg} ${cfg.border}`}>
            <div className="flex items-start gap-3">
              <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${cfg.text}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1.5">
                  <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full tracking-wide ${cfg.badge}`}>
                    {cfg.label.toUpperCase()}
                  </span>
                  <span className="text-slate-500 text-xs">
                    {item.mean_deviation_deg}° avg
                  </span>
                </div>
                <p className={`font-semibold text-sm ${cfg.text} mb-0.5`}>{item.cue}</p>
                <p className="text-slate-400 text-sm leading-relaxed">{item.explanation}</p>
              </div>
            </div>
          </div>
        )
      })}

      {summary && (
        <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700/60">
          <p className="text-slate-300 text-sm italic leading-relaxed">{summary}</p>
        </div>
      )}
    </div>
  )
}
