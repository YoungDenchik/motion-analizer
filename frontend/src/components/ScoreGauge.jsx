function scoreColor(score) {
  if (score >= 90) return '#4ade80'   // green-400
  if (score >= 80) return '#a3e635'   // lime-400
  if (score >= 70) return '#facc15'   // yellow-400
  if (score >= 60) return '#fb923c'   // orange-400
  return '#f87171'                    // red-400
}

export default function ScoreGauge({ score, grade, size = 140 }) {
  const r = size * 0.385          // radius as fraction of size
  const circ = 2 * Math.PI * r
  const filled = Math.max(0, Math.min(score / 100, 1)) * circ
  const color = scoreColor(score)
  const cx = size / 2
  const cy = size / 2

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Track */}
        <circle cx={cx} cy={cy} r={r}
          fill="none" stroke="#1e293b" strokeWidth="11" />
        {/* Progress */}
        <circle cx={cx} cy={cy} r={r}
          fill="none"
          stroke={color}
          strokeWidth="11"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circ}`}
          transform={`rotate(-90 ${cx} ${cy})`}
          style={{ transition: 'stroke-dasharray 1s ease-out' }}
        />
        {/* Score text */}
        <text x={cx} y={cy - 6}
          textAnchor="middle" dominantBaseline="middle"
          fill="white" fontSize={size * 0.195} fontWeight="700"
          fontFamily="system-ui, sans-serif">
          {Math.round(score)}
        </text>
        <text x={cx} y={cy + size * 0.12}
          textAnchor="middle" dominantBaseline="middle"
          fill="#94a3b8" fontSize={size * 0.085}
          fontFamily="system-ui, sans-serif">
          / 100
        </text>
      </svg>

      {/* Grade badge */}
      <div
        className="w-11 h-11 rounded-full flex items-center justify-center text-lg font-bold border-2"
        style={{ color, borderColor: color, backgroundColor: `${color}18` }}
      >
        {grade}
      </div>
    </div>
  )
}
