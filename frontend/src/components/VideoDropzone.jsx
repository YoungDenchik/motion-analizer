import { useRef, useState } from 'react'
import { Upload, Film, X } from 'lucide-react'

export default function VideoDropzone({ onFile, label = 'Drop video here' }) {
  const inputRef = useRef(null)
  const [file, setFile]       = useState(null)
  const [dragging, setDragging] = useState(false)

  function pick(f) {
    if (!f) return
    setFile(f)
    onFile(f)
  }

  function clear(e) {
    e.stopPropagation()
    setFile(null)
    onFile(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  if (file) {
    return (
      <div className="flex items-center gap-3 p-4 bg-slate-800/70 border border-slate-700 rounded-xl">
        <div className="w-9 h-9 bg-blue-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
          <Film className="w-4 h-4 text-blue-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-slate-200 text-sm font-medium truncate">{file.name}</p>
          <p className="text-slate-500 text-xs">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
        </div>
        <button onClick={clear}
          className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>
    )
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files[0]) }}
      className={`cursor-pointer border-2 border-dashed rounded-xl p-10 flex flex-col items-center gap-3 transition-all select-none ${
        dragging
          ? 'border-blue-400 bg-blue-500/8 scale-[1.01]'
          : 'border-slate-700 hover:border-slate-500 hover:bg-slate-800/40'
      }`}
    >
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${
        dragging ? 'bg-blue-500/20' : 'bg-slate-800'
      }`}>
        <Upload className={`w-5 h-5 transition-colors ${dragging ? 'text-blue-400' : 'text-slate-500'}`} />
      </div>
      <div className="text-center">
        <p className="text-slate-300 font-medium text-sm">{label}</p>
        <p className="text-slate-500 text-xs mt-1">or click to browse · MP4, MOV, AVI, MKV</p>
      </div>
      <input ref={inputRef} type="file"
        accept=".mp4,.mov,.avi,.mkv,.webm"
        className="hidden"
        onChange={e => pick(e.target.files[0])} />
    </div>
  )
}
