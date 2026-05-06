import { useState } from 'react'
import { CheckCircle, Loader2, AlertCircle, RotateCcw, Info } from 'lucide-react'
import { api } from '../api'
import VideoDropzone from '../components/VideoDropzone'

export default function Record() {
  const [name,      setName]      = useState('')
  const [desc,      setDesc]      = useState('')
  const [overwrite, setOverwrite] = useState(false)
  const [videoFile, setVideoFile] = useState(null)
  const [phase,     setPhase]     = useState('idle')   // idle | loading | done | error
  const [result,    setResult]    = useState(null)
  const [error,     setError]     = useState('')

  const canSubmit = name.trim() && videoFile && phase !== 'loading'

  async function handleSubmit() {
    setPhase('loading')
    setError('')
    setResult(null)
    try {
      const { job_id } = await api.recordReference(name.trim(), desc.trim(), videoFile, overwrite)
      const res = await api.pollUntilDone(job_id, () => {}, 2000)
      setResult(res)
      setPhase('done')
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Recording failed'
      setError(msg)
      setPhase('error')
    }
  }

  function reset() {
    setPhase('idle')
    setResult(null)
    setError('')
    setVideoFile(null)
    setName('')
    setDesc('')
    setOverwrite(false)
  }

  if (phase === 'done' && result) {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <div className="mb-7">
          <h1 className="text-2xl font-bold text-white mb-1">Record Reference</h1>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 text-center">
          <div className="w-16 h-16 bg-green-500/15 rounded-full flex items-center justify-center mx-auto mb-5">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Reference Saved!</h2>
          <p className="text-slate-400 mb-1">
            <span className="text-blue-300 font-mono font-medium">{result.name}</span> recorded successfully.
          </p>
          <p className="text-slate-500 text-sm mb-8">
            {result.num_frames} frames · {Number(result.fps).toFixed(0)} fps
          </p>
          <button onClick={reset}
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-sm font-medium transition-colors border border-slate-700">
            <RotateCcw className="w-4 h-4" />
            Record Another
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <div className="mb-7">
        <h1 className="text-2xl font-bold text-white mb-1">Record Reference</h1>
        <p className="text-slate-400 text-sm">
          Upload a video of correct technique. Multiple reps per video are supported —
          they are automatically averaged into a single canonical template.
        </p>
      </div>

      {/* Naming tip */}
      <div className="flex items-start gap-3 p-4 bg-blue-500/8 border border-blue-500/20 rounded-xl mb-6">
        <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
        <p className="text-slate-400 text-sm leading-relaxed">
          Use underscore suffixes for multiple angles of the same exercise:{' '}
          <span className="font-mono text-blue-300">squat</span>,{' '}
          <span className="font-mono text-blue-300">squat_front</span>,{' '}
          <span className="font-mono text-blue-300">squat_lowbar</span>.{' '}
          The best match is selected automatically at analysis time.
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Exercise Name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="squat  /  squat_front  /  deadlift"
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 transition-colors font-mono text-sm"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
          <input
            type="text"
            value={desc}
            onChange={e => setDesc(e.target.value)}
            placeholder="e.g. Standard barbell back squat, side view"
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 transition-colors text-sm"
          />
        </div>

        {/* Video */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Reference Video <span className="text-red-400">*</span>
          </label>
          <VideoDropzone onFile={setVideoFile} label="Drop reference video here" />
        </div>

        {/* Overwrite */}
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={overwrite}
            onChange={e => setOverwrite(e.target.checked)}
            className="w-4 h-4 rounded accent-blue-500 bg-slate-800 border-slate-600"
          />
          <span className="text-slate-400 text-sm">Overwrite if this name already exists</span>
        </label>

        {/* Error */}
        {phase === 'error' && (
          <div className="flex items-start gap-3 p-4 bg-red-500/8 border border-red-500/25 rounded-xl">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full py-3 bg-blue-500 hover:bg-blue-600 active:bg-blue-700 disabled:opacity-35 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
        >
          {phase === 'loading'
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Processing video…</>
            : 'Record Reference'}
        </button>
      </div>
    </div>
  )
}
