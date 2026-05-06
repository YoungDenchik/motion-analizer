import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Loader2, ChevronDown, RotateCcw, AlertCircle,
  Clock, Layers, TrendingUp, Gauge, Film,
} from 'lucide-react'
import { api } from '../api'
import VideoDropzone from '../components/VideoDropzone'
import ScoreGauge    from '../components/ScoreGauge'
import RepChart      from '../components/RepChart'
import FeedbackPanel from '../components/FeedbackPanel'

// Rotating status messages shown while the pipeline runs
const STAGES = [
  'Uploading video…',
  'Detecting pose landmarks…',
  'Extracting joint angles…',
  'Segmenting repetitions…',
  'Running FastDTW comparison…',
  'Applying tolerance band…',
  'Classifying errors…',
  'Generating feedback…',
  'Rendering annotated video…',
]

function StatCard({ label, value, sub, accent }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
      <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ?? 'text-white'}`}>{value}</p>
      {sub && <p className="text-slate-500 text-xs mt-0.5">{sub}</p>}
    </div>
  )
}

export default function Analyze() {
  const [exercises, setExercises] = useState([])
  const [videoFile, setVideoFile] = useState(null)
  const [exercise,  setExercise]  = useState('')
  const [phase,     setPhase]     = useState('idle')   // idle | loading | done | error
  const [stageIdx,  setStageIdx]  = useState(0)
  const [result,    setResult]    = useState(null)
  const [jobId,     setJobId]     = useState(null)
  const [error,     setError]     = useState('')

  useEffect(() => {
    api.listReferences().then(d => {
      setExercises(d.exercises)
      if (d.exercises.length) setExercise(d.exercises[0])
    }).catch(() => {})
  }, [])

  const canAnalyze = videoFile && exercise && phase !== 'loading'

  async function handleAnalyze() {
    setPhase('loading')
    setStageIdx(0)
    setResult(null)
    setError('')

    const timer = setInterval(() => setStageIdx(i => (i + 1) % STAGES.length), 4000)

    try {
      const { job_id } = await api.startAnalysis(exercise, videoFile)
      setJobId(job_id)
      const res = await api.pollUntilDone(job_id, () => {}, 2000)
      clearInterval(timer)
      setResult(res)
      setPhase('done')
    } catch (e) {
      clearInterval(timer)
      setError(e.message || 'Analysis failed. Check the backend logs.')
      setPhase('error')
    }
  }

  function reset() {
    setPhase('idle')
    setResult(null)
    setJobId(null)
    setError('')
    setVideoFile(null)
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-7">
        <h1 className="text-2xl font-bold text-white mb-1">Analyze Video</h1>
        <p className="text-slate-400 text-sm">
          Upload a workout video and compare it rep-by-rep against a stored reference.
        </p>
      </div>

      {/* ── Upload form (hidden after success) ───────────────────────────── */}
      {phase !== 'done' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Workout Video</label>
            <VideoDropzone onFile={setVideoFile} label="Drop your workout video here" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Exercise</label>
            {exercises.length === 0 ? (
              <p className="text-slate-500 text-sm py-2">
                No references stored yet.{' '}
                <Link to="/record" className="text-blue-400 hover:underline">Record one first →</Link>
              </p>
            ) : (
              <div className="relative">
                <select
                  value={exercise}
                  onChange={e => setExercise(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 appearance-none pr-10 focus:outline-none focus:border-blue-500 transition-colors font-mono text-sm"
                >
                  {exercises.map(ex => (
                    <option key={ex} value={ex}>{ex}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
              </div>
            )}
          </div>

          <button
            onClick={handleAnalyze}
            disabled={!canAnalyze}
            className="w-full py-3 bg-blue-500 hover:bg-blue-600 active:bg-blue-700 disabled:opacity-35 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {phase === 'loading' ? <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing…</> : 'Analyze'}
          </button>

          {/* Loading progress */}
          {phase === 'loading' && (
            <div className="space-y-2 pt-1">
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400 flex-shrink-0" />
                <span className="truncate">{STAGES[stageIdx]}</span>
              </div>
              <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full"
                  style={{ width: `${((stageIdx + 1) / STAGES.length) * 100}%`, transition: 'width 3.8s ease' }} />
              </div>
            </div>
          )}

          {/* Error */}
          {phase === 'error' && (
            <div className="flex items-start gap-3 p-4 bg-red-500/8 border border-red-500/25 rounded-xl">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-400 font-semibold text-sm mb-0.5">Analysis failed</p>
                <p className="text-slate-400 text-sm">{error}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Results ──────────────────────────────────────────────────────── */}
      {phase === 'done' && result && (
        <div className="space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white capitalize">{result.exercise_name}</h2>
              <p className="text-slate-500 text-sm">{result.num_reps} rep{result.num_reps !== 1 ? 's' : ''} · {result.duration_seconds}s · {result.detected_frame_count} frames</p>
            </div>
            <button onClick={reset}
              className="flex items-center gap-2 text-slate-400 hover:text-slate-200 text-sm px-3 py-2 rounded-xl hover:bg-slate-800 transition-colors border border-transparent hover:border-slate-700">
              <RotateCcw className="w-3.5 h-3.5" />
              New Analysis
            </button>
          </div>

          {/* Annotated video — or reason it failed */}
          {result.render_error && (
            <div className="flex items-start gap-3 p-4 bg-yellow-500/8 border border-yellow-500/25 rounded-xl">
              <AlertCircle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-yellow-400 font-semibold text-sm mb-0.5">Annotated video unavailable</p>
                <p className="text-slate-400 text-xs font-mono">{result.render_error}</p>
              </div>
            </div>
          )}
          {result.has_annotated_video && jobId && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
              <div className="flex items-center justify-between px-6 pt-5 pb-3">
                <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
                  <Film className="w-4 h-4 text-blue-400" />
                  Annotated Video
                </h3>
                <a
                  href={`/api/video/${jobId}`}
                  download={`${result.exercise_name}_annotated.mp4`}
                  className="text-xs text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-lg hover:bg-slate-800 border border-slate-700 hover:border-slate-600 transition-colors"
                >
                  Download
                </a>
              </div>
              <video
                src={`/api/video/${jobId}`}
                controls
                className="w-full max-h-[60vh] bg-black"
                preload="metadata"
              />
            </div>
          )}

          {/* Score row */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-1 bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col items-center justify-center gap-3">
              <ScoreGauge score={result.overall_score} grade={result.grade} />
              <p className="text-slate-400 text-xs text-center leading-relaxed">{result.feedback.grade_message}</p>
            </div>
            <div className="md:col-span-3 grid grid-cols-2 sm:grid-cols-3 gap-3">
              <StatCard label="Reps"        value={result.num_reps}             sub="detected" />
              <StatCard label="Duration"    value={`${result.duration_seconds}s`} sub={`${result.detected_frame_count} frames`} />
              <StatCard label="Consistency" value={`±${result.score_consistency}°`}
                sub={result.score_consistency < 5 ? '● Stable' : '● Variable'}
                accent={result.score_consistency < 5 ? 'text-green-400' : 'text-yellow-400'} />
              <StatCard label="Best Rep"
                value={`Rep ${result.best_rep_index + 1}`}
                sub={`${result.per_rep_scores[result.best_rep_index]?.toFixed(1)}/100`}
                accent="text-green-400" />
              <StatCard label="Worst Rep"
                value={`Rep ${result.worst_rep_index + 1}`}
                sub={`${result.per_rep_scores[result.worst_rep_index]?.toFixed(1)}/100`}
                accent="text-orange-400" />
              <StatCard label="Processed in" value={`${result.processing_time_seconds}s`} sub="analysis time" />
            </div>
          </div>

          {/* Rep chart + Feedback */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2 text-sm">
                <Layers className="w-4 h-4 text-blue-400" />
                Per-Rep Scores
              </h3>
              {result.per_rep_scores.length > 0
                ? <RepChart perRepScores={result.per_rep_scores} bestIdx={result.best_rep_index} worstIdx={result.worst_rep_index} />
                : <p className="text-slate-500 text-sm">No reps detected.</p>}
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2 text-sm">
                <TrendingUp className="w-4 h-4 text-blue-400" />
                Coaching Feedback
              </h3>
              <FeedbackPanel feedback={result.feedback} />
            </div>
          </div>

          {/* Error event table (only if there are events) */}
          {result.error_events.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2 text-sm">
                <Gauge className="w-4 h-4 text-blue-400" />
                Deviation Detail
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800">
                      {['Feature', 'Severity', 'Direction', 'Avg °', 'Max °', '% frames'].map(h => (
                        <th key={h} className="text-left pb-2 pr-4 text-slate-500 text-xs font-semibold uppercase tracking-wide">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.error_events.map((ev, i) => (
                      <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                        <td className="py-2 pr-4 font-mono text-slate-300 text-xs">{ev.feature_name}</td>
                        <td className="py-2 pr-4">
                          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                            ev.severity === 'critical' ? 'bg-red-500/15 text-red-400' : 'bg-yellow-500/15 text-yellow-400'
                          }`}>{ev.severity}</span>
                        </td>
                        <td className="py-2 pr-4 text-slate-400 text-xs capitalize">{ev.direction}</td>
                        <td className="py-2 pr-4 text-slate-300 font-mono text-xs">{ev.mean_deviation_deg}°</td>
                        <td className="py-2 pr-4 text-slate-300 font-mono text-xs">{ev.max_deviation_deg}°</td>
                        <td className="py-2 text-slate-400 text-xs">{(ev.affected_frame_ratio * 100).toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
