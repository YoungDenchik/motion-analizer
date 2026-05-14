import { useState } from 'react'
import { Upload, Camera } from 'lucide-react'
import VideoDropzone from './VideoDropzone'
import CameraRecorder from './CameraRecorder'

export default function VideoInput({ onFile, label = 'Drop video here' }) {
  const [mode, setMode] = useState('upload')  // 'upload' | 'camera'

  function switchMode(next) {
    if (next === mode) return
    onFile(null)   // clear any selected file when switching tabs
    setMode(next)
  }

  return (
    <div>
      {/* Tab switcher */}
      <div className="flex gap-1 p-1 bg-slate-800/60 border border-slate-700/60 rounded-xl mb-3 w-fit">
        <button
          onClick={() => switchMode('upload')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            mode === 'upload'
              ? 'bg-slate-700 text-slate-200 shadow-sm'
              : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          <Upload className="w-3 h-3" />
          Upload file
        </button>
        <button
          onClick={() => switchMode('camera')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            mode === 'camera'
              ? 'bg-slate-700 text-slate-200 shadow-sm'
              : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          <Camera className="w-3 h-3" />
          Record live
        </button>
      </div>

      {mode === 'upload' && <VideoDropzone onFile={onFile} label={label} />}
      {mode === 'camera' && <CameraRecorder onFile={onFile} />}
    </div>
  )
}
