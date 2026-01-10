import React from 'react'
import { ShieldAlert } from 'lucide-react'

export default function IncidentCard({incidents=[]}){
  return (
    <div className="bg-card rounded border border-card-border p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="text-rose-400" />
          <h4 className="font-semibold">Active Incidents</h4>
        </div>
        <div className="text-xs text-slate-400">{incidents.length} Open</div>
      </div>

      <div className="mt-4">
        {incidents.length === 0 ? (
          <div className="text-sm text-slate-400">No active incidents</div>
        ) : (
          <ul className="space-y-3">
            {incidents.map(i=> (
              <li key={i.id} className="bg-gray-50 p-2 rounded border border-card-border/60">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold">{i.title}</div>
                  <div className="text-xs text-slate-300">{Math.round(i.confidence*100)}%</div>
                </div>
                <div className="text-xs text-slate-400 mt-1">{i.details}</div>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-4">
          <div className="text-xs text-slate-400">Model Confidence</div>
          <div className="w-full bg-gray-100 rounded h-3 mt-2">
            <div className="h-3 rounded bg-gray-400" style={{width:'94%'}} />
          </div>
        </div>
      </div>
    </div>
  )
}
