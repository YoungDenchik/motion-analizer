import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, Cell, ResponsiveContainer,
} from 'recharts'

function scoreColor(score) {
  if (score >= 90) return '#4ade80'
  if (score >= 80) return '#a3e635'
  if (score >= 70) return '#facc15'
  if (score >= 60) return '#fb923c'
  return '#f87171'
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const { rep, score, isBest, isWorst } = payload[0].payload
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-3 text-sm shadow-xl">
      <p className="text-slate-400 mb-1">Rep {rep}</p>
      <p className="font-bold text-base" style={{ color: scoreColor(score) }}>
        {score.toFixed(1)} / 100
      </p>
      {isBest  && <p className="text-green-400 text-xs mt-1">★ Best rep</p>}
      {isWorst && <p className="text-orange-400 text-xs mt-1">⚠ Needs work</p>}
    </div>
  )
}

export default function RepChart({ perRepScores, bestIdx, worstIdx }) {
  const data = perRepScores.map((score, i) => ({
    rep: i + 1,
    score,
    isBest:  i === bestIdx,
    isWorst: i === worstIdx,
  }))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 16, left: -10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis
          dataKey="rep"
          tick={{ fill: '#64748b', fontSize: 12 }}
          label={{ value: 'Rep', position: 'insideBottom', offset: -4, fill: '#475569', fontSize: 11 }}
          axisLine={false} tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: '#64748b', fontSize: 11 }}
          axisLine={false} tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#ffffff08', radius: 6 }} />
        <ReferenceLine y={70} stroke="#334155" strokeDasharray="4 4" label={{ value: '70', fill: '#475569', fontSize: 10 }} />
        <Bar dataKey="score" radius={[5, 5, 0, 0]} maxBarSize={56}>
          {data.map(entry => (
            <Cell key={entry.rep} fill={scoreColor(entry.score)}
              opacity={entry.isBest || entry.isWorst ? 1 : 0.75} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
