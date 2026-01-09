import React from 'react'
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from 'recharts'

const data = Array.from({length:30}).map((_,i)=>{
  if(i < 15) return {day: `D${i+1}`, value: 20}
  if(i < 25) return {day: `D${i+1}`, value: 60}
  return {day: `D${i+1}`, value: 95}
})

export default function TimelineChart(){
  return (
    <div className="mt-4 h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{top:10,right:30,left:0,bottom:0}}>
          <defs>
            <linearGradient id="colorPhase" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#EF4444" stopOpacity={0.9}/>
              <stop offset="60%" stopColor="#F59E0B" stopOpacity={0.6}/>
              <stop offset="100%" stopColor="#10B981" stopOpacity={0.2}/>
            </linearGradient>
          </defs>
          <XAxis dataKey="day" tick={{fontSize:10}} stroke="#94a3b8" />
          <Tooltip contentStyle={{background:'#0f172a', borderColor:'#334155'}} />
          <Area type="monotone" dataKey="value" stroke="#0ea5a4" fill="url(#colorPhase)" />
        </AreaChart>
      </ResponsiveContainer>
      <div className="mt-3 flex items-center justify-end">
        <div className="bg-rose-600 animate-pulse px-3 py-2 rounded font-bold">STAGE: EXFILTRATION</div>
      </div>
    </div>
  )
}
