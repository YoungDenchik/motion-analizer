import { useRef, useState, useEffect } from 'react'
import { Camera, Circle, Square, RotateCcw, CheckCircle, AlertCircle } from 'lucide-react'

function fmt(s) {
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

// Pick the best MIME type the browser supports for recording
function bestMime() {
  const candidates = [
    'video/webm;codecs=h264',
    'video/webm;codecs=vp9',
    'video/webm;codecs=vp8',
    'video/webm',
    'video/mp4',
  ]
  return candidates.find(t => MediaRecorder.isTypeSupported(t)) ?? ''
}

export default function CameraRecorder({ onFile }) {
  const videoRef    = useRef(null)
  const recorderRef = useRef(null)
  const chunksRef   = useRef([])
  const streamRef   = useRef(null)
  const timerRef    = useRef(null)

  const [phase,       setPhase]       = useState('idle')   // idle|preview|recording|done|error
  const [recordedUrl, setRecordedUrl] = useState(null)
  const [duration,    setDuration]    = useState(0)
  const [errMsg,      setErrMsg]      = useState('')

  // Cleanup on unmount
  useEffect(() => () => {
    clearInterval(timerRef.current)
    streamRef.current?.getTracks().forEach(t => t.stop())
    if (recordedUrl) URL.revokeObjectURL(recordedUrl)
  }, [recordedUrl])

  async function enableCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
      }
      setPhase('preview')
    } catch (e) {
      setErrMsg(`Camera access denied: ${e.message}`)
      setPhase('error')
    }
  }

  function startRecording() {
    chunksRef.current = []
    const mime = bestMime()
    const recorder = new MediaRecorder(streamRef.current, mime ? { mimeType: mime } : {})

    recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
    recorder.onstop = () => {
      const mimeType = recorder.mimeType || 'video/webm'
      const blob = new Blob(chunksRef.current, { type: mimeType })
      const ext  = mimeType.includes('mp4') ? 'mp4' : 'webm'
      const file = new File([blob], `recording.${ext}`, { type: mimeType })
      const url  = URL.createObjectURL(blob)
      setRecordedUrl(url)
      setPhase('done')
      onFile(file)
      streamRef.current?.getTracks().forEach(t => t.stop())
    }

    recorder.start(100)
    recorderRef.current = recorder
    setDuration(0)
    setPhase('recording')
    timerRef.current = setInterval(() => setDuration(d => d + 1), 1000)
  }

  function stopRecording() {
    clearInterval(timerRef.current)
    recorderRef.current?.stop()
  }

  function reset() {
    clearInterval(timerRef.current)
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    if (recordedUrl) URL.revokeObjectURL(recordedUrl)
    setRecordedUrl(null)
    setPhase('idle')
    setDuration(0)
    setErrMsg('')
    onFile(null)
  }

  // ── Error ───────────────────────────────────────────────────────────────────
  if (phase === 'error') return (
    <div className="p-5 bg-red-500/10 border border-red-500/25 rounded-xl flex flex-col items-center gap-3 text-center">
      <AlertCircle className="w-6 h-6 text-red-400" />
      <p className="text-red-400 text-sm">{errMsg}</p>
      <button onClick={() => setPhase('idle')} className="text-xs text-slate-400 hover:text-slate-200">
        Try again
      </button>
    </div>
  )

  // ── Done — show playback ────────────────────────────────────────────────────
  if (phase === 'done') return (
    <div className="space-y-3">
      <div className="rounded-xl overflow-hidden bg-black">
        <video src={recordedUrl} controls className="w-full max-h-64 object-contain" />
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-green-500/10 border border-green-500/25 rounded-xl">
          <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
          <span className="text-green-400 text-sm font-medium">Recording ready · {fmt(duration)}</span>
        </div>
        <button
          onClick={reset}
          className="px-3 py-2 text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-sm transition-colors flex items-center gap-1.5"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Redo
        </button>
      </div>
    </div>
  )

  // ── Idle — prompt to open camera ────────────────────────────────────────────
  if (phase === 'idle') return (
    <button
      onClick={enableCamera}
      className="w-full border-2 border-dashed border-slate-700 hover:border-slate-500 hover:bg-slate-800/40 rounded-xl p-10 flex flex-col items-center gap-3 transition-all"
    >
      <div className="w-12 h-12 bg-slate-800 rounded-xl flex items-center justify-center">
        <Camera className="w-5 h-5 text-slate-500" />
      </div>
      <div className="text-center">
        <p className="text-slate-300 font-medium text-sm">Enable camera</p>
        <p className="text-slate-500 text-xs mt-1">Records directly from your webcam · no file needed</p>
      </div>
    </button>
  )

  // ── Preview / Recording — live camera feed ──────────────────────────────────
  return (
    <div className="space-y-3">
      <div className="relative rounded-xl overflow-hidden bg-black aspect-video">
        <video ref={videoRef} muted playsInline className="w-full h-full object-cover" />

        {phase === 'recording' && (
          <div className="absolute top-3 left-3 flex items-center gap-2 bg-black/60 backdrop-blur-sm px-3 py-1.5 rounded-full">
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            <span className="text-white text-xs font-mono font-semibold">{fmt(duration)}</span>
          </div>
        )}
        {phase === 'preview' && (
          <div className="absolute top-3 left-3 px-2.5 py-1 bg-black/60 backdrop-blur-sm rounded-full">
            <span className="text-slate-300 text-xs">Live preview</span>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        {phase === 'preview' && (
          <button
            onClick={startRecording}
            className="flex-1 py-2.5 bg-red-500 hover:bg-red-600 active:bg-red-700 text-white font-semibold rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
          >
            <Circle className="w-3.5 h-3.5 fill-white" />
            Start Recording
          </button>
        )}
        {phase === 'recording' && (
          <button
            onClick={stopRecording}
            className="flex-1 py-2.5 bg-slate-700 hover:bg-slate-600 active:bg-slate-500 text-white font-semibold rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
          >
            <Square className="w-3.5 h-3.5 fill-white" />
            Stop Recording
          </button>
        )}
        <button
          onClick={reset}
          className="px-3 py-2 text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl text-sm transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
