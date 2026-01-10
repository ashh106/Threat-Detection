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
          <XAxis dataKey="day" tick={{fontSize:10}} stroke="#9CA3AF" />
          <Tooltip contentStyle={{background:'#FFFFFF', borderColor:'#E5E7EB', fontSize:11}} />
          <Area type="monotone" dataKey="value" stroke="#4B5563" fill="#E5E7EB" />
        </AreaChart>
      </ResponsiveContainer>
      <div className="mt-3 flex items-center justify-end">
        <div className="px-3 py-1 rounded border border-card-border text-[11px] text-slate-700 bg-white">Phase progression (demo)</div>
      </div>
    </div>
  )
}
