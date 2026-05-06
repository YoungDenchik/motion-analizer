import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Library as LibIcon, Plus, RefreshCw, Trash2, Video } from 'lucide-react'
import { api } from '../api'

export default function Library() {
  const [exercises, setExercises] = useState([])
  const [loading,   setLoading]   = useState(true)
  const [deleting,  setDeleting]  = useState(null)

  function load() {
    setLoading(true)
    api.listReferences()
      .then(d => setExercises(d.exercises))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  async function handleDelete(name) {
    if (!window.confirm(`Delete reference "${name}"?\nThis cannot be undone.`)) return
    setDeleting(name)
    try {
      await api.deleteReference(name)
      setExercises(prev => prev.filter(e => e !== name))
    } catch (e) {
      alert('Failed to delete: ' + (e.response?.data?.detail || e.message))
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-7">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Exercise Library</h1>
          <p className="text-slate-400 text-sm">
            {loading ? 'Loading…' : `${exercises.length} reference${exercises.length !== 1 ? 's' : ''} stored`}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={load}
            className="p-2.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-xl transition-colors border border-transparent hover:border-slate-700"
            title="Refresh">
            <RefreshCw className="w-4 h-4" />
          </button>
          <Link to="/record"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold rounded-xl transition-colors">
            <Plus className="w-4 h-4" />
            Add Reference
          </Link>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-slate-900 border border-slate-800 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : exercises.length === 0 ? (
        <div className="text-center py-24">
          <div className="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-5">
            <LibIcon className="w-8 h-8 text-slate-600" />
          </div>
          <h2 className="text-slate-300 font-semibold mb-2">Library is empty</h2>
          <p className="text-slate-500 text-sm mb-7">
            Record your first exercise reference to get started.
          </p>
          <Link to="/record"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-xl text-sm transition-colors">
            <Plus className="w-4 h-4" />
            Record Reference
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {exercises.map(name => (
            <div key={name}
              className="group flex items-center gap-4 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl p-5 transition-all">
              {/* Icon */}
              <div className="w-11 h-11 bg-blue-500/10 border border-blue-500/15 rounded-xl flex items-center justify-center flex-shrink-0">
                <LibIcon className="w-5 h-5 text-blue-400" />
              </div>

              {/* Name */}
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-white font-mono text-sm">{name}</p>
                <p className="text-slate-500 text-xs mt-0.5">Reference exercise</p>
              </div>

              {/* Actions (visible on hover) */}
              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <Link to="/analyze"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-400 hover:text-blue-300 border border-blue-500/30 hover:border-blue-400/50 rounded-lg transition-colors">
                  <Video className="w-3 h-3" />
                  Analyze
                </Link>
                <button
                  onClick={() => handleDelete(name)}
                  disabled={deleting === name}
                  className="p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-40"
                  title={`Delete ${name}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
