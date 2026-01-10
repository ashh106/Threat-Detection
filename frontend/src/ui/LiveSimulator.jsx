import React, { useState } from 'react'
import { Cpu, AlertCircle } from 'lucide-react'

const SAMPLE_EVENTS = [
  {
    time: '09:00',
    user: 'USER001',
    action: 'Logon',
    resource: 'WS-01',
    bytes: 0,
    intent: 'Normal access'
  },
  {
    time: '09:12',
    user: 'USER001',
    action: 'Open document',
    resource: 'DesignSpec.docx',
    bytes: 524_288,
    intent: 'Exploration'
  },
  {
    time: '09:18',
    user: 'USER001',
    action: 'Bulk export',
    resource: 'CustomerDB',
    bytes: 50 * 1024 * 1024 * 1024,
    intent: 'High‑risk exfiltration'
  }
]

export default function LiveSimulator(){
  const [events, setEvents] = useState([])
  const [risk, setRisk] = useState('safe')

  const addEvent = () => {
    const next = SAMPLE_EVENTS[events.length % SAMPLE_EVENTS.length]
    setEvents(prev => [next, ...prev])
    if(next.intent.includes('High‑risk')){
      setRisk('critical')
    } else if(next.intent.includes('Exploration')){
      setRisk('warning')
    } else {
      setRisk('safe')
    }
  }

  const latest = events[0]

  return (
    <div className="bg-card rounded-lg border border-card-border p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="text-slate-700" />
          <h3 className="font-semibold text-slate-900">Live Event Simulator</h3>
        </div>
        <div className="text-xs text-slate-500">Sample telemetry</div>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-slate-700">
        <div>
          {latest ? (
            <div>
              <div><span className="font-semibold">Last event:</span> {latest.time} {latest.user} {latest.action} on {latest.resource}</div>
              <div className="text-slate-600">Model intent: {latest.intent}</div>
            </div>
          ) : (
            <div>No events yet. Click "Generate event" to simulate activity.</div>
          )}
        </div>
        <button
          type="button"
          onClick={addEvent}
          className="px-3 py-1.5 rounded border border-card-border text-xs text-slate-800 bg-white hover:bg-gray-50"
        >
          Generate event
        </button>
      </div>

      <div className="mt-4 flex gap-4">
        <div className="flex-1">
          <div className="h-44 overflow-y-auto bg-gray-50 p-3 rounded text-xs font-mono text-slate-800 border border-card-border/60">
            {events.length === 0 ? (
              <div className="text-slate-500">No simulated raw metadata yet.</div>
            ) : (
              events.map((e, idx) => (
                <div key={idx} className="py-1 border-b border-gray-200 last:border-0">
                  [{e.time}] {e.user} {e.action} {e.resource} bytes={e.bytes.toLocaleString()} | intent={e.intent}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="w-40 flex flex-col items-center justify-center">
          <div className={`w-20 h-20 rounded-full flex items-center justify-center border border-card-border ${risk === 'critical' ? 'bg-gray-200' : risk === 'warning' ? 'bg-gray-100' : 'bg-gray-50'}`}>
            {risk === 'critical' ? <AlertCircle className="text-slate-800"/> : <Cpu className="text-slate-800"/>}
          </div>
          <div className="text-xs mt-2 text-slate-700">
            {risk === 'critical' ? 'Alert: high‑risk behavior' : risk === 'warning' ? 'Elevated exploration' : 'Normal activity'}
          </div>
        </div>
      </div>
    </div>
  )
}
