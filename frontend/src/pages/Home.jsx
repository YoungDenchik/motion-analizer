import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, Video, BookOpen, Library, ChevronRight, Zap } from 'lucide-react'
import { api } from '../api'

const CARDS = [
  {
    to: '/analyze',
    Icon: Video,
    gradient: 'from-blue-500 to-blue-600',
    glow: 'hover:shadow-blue-500/20',
    ring: 'ring-blue-500/20',
    title: 'Analyze Video',
    desc: 'Upload a workout video and get instant rep-by-rep technique feedback with a 0–100 score.',
    cta: 'Start Analysis',
  },
  {
    to: '/record',
    Icon: BookOpen,
    gradient: 'from-violet-500 to-purple-600',
    glow: 'hover:shadow-violet-500/20',
    ring: 'ring-violet-500/20',
    title: 'Record Reference',
    desc: 'Upload a video of ideal technique to use as the comparison template for any exercise.',
    cta: 'Add Reference',
  },
  {
    to: '/library',
    Icon: Library,
    gradient: 'from-emerald-500 to-teal-600',
    glow: 'hover:shadow-emerald-500/20',
    ring: 'ring-emerald-500/20',
    title: 'Exercise Library',
    desc: 'Browse and manage all stored reference exercises. Delete or inspect any entry.',
    cta: 'Open Library',
  },
]

export default function Home() {
  const [exercises, setExercises] = useState([])

  useEffect(() => {
    api.listReferences().then(d => setExercises(d.exercises)).catch(() => {})
  }, [])

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Hero */}
      <div className="mb-10">
        <div className="inline-flex items-center gap-2 text-blue-400 text-xs font-semibold tracking-widest uppercase mb-4 px-3 py-1.5 bg-blue-500/10 rounded-full border border-blue-500/20">
          <Zap className="w-3 h-3" />
          AI-Powered Technique Analysis
        </div>
        <h1 className="text-4xl font-bold text-white mb-3 leading-tight">
          AI Fitness Coach
        </h1>
        <p className="text-slate-400 text-lg max-w-2xl leading-relaxed">
          Upload your workout video and get instant, rep-by-rep technique feedback
          compared against an expert reference — powered by MediaPipe and Dynamic Time Warping.
        </p>
      </div>

      {/* Action cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10">
        {CARDS.map(({ to, Icon, gradient, glow, ring, title, desc, cta }) => (
          <Link key={to} to={to}
            className={`group bg-slate-900 border border-slate-800 rounded-2xl p-6 transition-all
              hover:border-slate-700 hover:-translate-y-0.5 hover:shadow-xl ${glow}
              hover:ring-2 ${ring}`}
          >
            <div className={`w-11 h-11 bg-gradient-to-br ${gradient} rounded-xl flex items-center justify-center mb-5 shadow-lg`}>
              <Icon className="w-5 h-5 text-white" />
            </div>
            <h2 className="font-bold text-white text-base mb-2">{title}</h2>
            <p className="text-slate-400 text-sm leading-relaxed mb-5">{desc}</p>
            <span className="text-blue-400 text-sm font-medium flex items-center gap-1 group-hover:gap-2 transition-all">
              {cta}
              <ChevronRight className="w-4 h-4" />
            </span>
          </Link>
        ))}
      </div>

      {/* Pipeline overview */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6">
        <h3 className="text-slate-200 font-semibold mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-400" />
          How it works
        </h3>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {['Video upload', 'Pose detection (33 landmarks)', '9 joint angles', 'Rep segmentation (PCA)', 'DTW alignment', 'Score 0–100', 'Coaching feedback'].map((step, i, arr) => (
            <div key={step} className="flex items-center gap-2">
              <span className="px-3 py-1 bg-slate-800 border border-slate-700 rounded-lg text-slate-300 text-xs font-medium">{step}</span>
              {i < arr.length - 1 && <span className="text-slate-600 text-xs">→</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Stored references */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-slate-200 font-semibold">Stored References</h3>
          <span className="text-slate-500 text-xs">{exercises.length} exercise{exercises.length !== 1 ? 's' : ''}</span>
        </div>
        {exercises.length === 0 ? (
          <p className="text-slate-500 text-sm">
            No references yet.{' '}
            <Link to="/record" className="text-blue-400 hover:text-blue-300 hover:underline transition-colors">
              Record your first one →
            </Link>
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {exercises.map(name => (
              <Link key={name} to="/analyze"
                className="px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 text-blue-300 text-sm rounded-lg hover:bg-blue-500/20 transition-colors font-mono">
                {name}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
