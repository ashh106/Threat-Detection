import React, { useEffect, useState, useRef } from 'react'
import { Cpu, AlertCircle } from 'lucide-react'

const logs = [
  '[09:00] User Login (Normal)',
  '[09:15] Access Sensitive DB (Risk: Low)',
  '[09:20] Bulk Export 50GB (Risk: CRITICAL 🔴)'
]

export default function LiveSimulator(){
  const [index, setIndex] = useState(0)
  const [risk, setRisk] = useState('safe')
  const listRef = useRef()

  useEffect(()=>{
    const id = setInterval(()=>{
      setIndex((i)=> (i+1)%logs.length)
      const l = logs[(index+1)%logs.length]
      if(l.includes('CRITICAL')){
        setRisk('critical')
      } else if(l.includes('Low')){
        setRisk('warning')
      } else {
        setRisk('safe')
      }
    }, 1500)

    return ()=>clearInterval(id)
  },[index])

  useEffect(()=>{
    if(listRef.current){
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  },[index])

  return (
    <div className="bg-card rounded-lg border border-card-border p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="text-slate-200" />
          <h3 className="font-semibold">Live Threat Simulator</h3>
        </div>
        <div className="text-xs text-slate-400">Demo</div>
      </div>

      <div className="mt-4 flex gap-4">
        <div className="flex-1">
          <div ref={listRef} className="h-48 overflow-y-auto bg-[#071127] p-3 rounded text-xs font-mono text-slate-200">
            {Array.from({length: 6}).map((_,i)=>{
              const msg = logs[(index + i) % logs.length]
              const isCritical = msg.includes('CRITICAL')
              return <div key={i} className={`py-1 ${isCritical ? 'text-rose-400 font-semibold' : 'text-slate-300'}`}>{msg}</div>
            })}
          </div>
        </div>

        <div className="w-36 flex flex-col items-center justify-center">
          <div className={`w-20 h-20 rounded-full flex items-center justify-center ${risk === 'critical' ? 'bg-gradient-to-br from-rose-600 to-rose-400 animate-pulse' : risk === 'warning' ? 'bg-amber-500' : 'bg-emerald-500'}`}>
            {risk === 'critical' ? <AlertCircle className="text-white"/> : <Cpu className="text-white"/>}
          </div>
          <div className="text-xs mt-2 text-slate-300">Risk Gauge</div>
        </div>
      </div>
    </div>
  )
}
