import React from 'react'
import LiveSimulator from '../ui/LiveSimulator'
import DataCompatibility from '../ui/DataCompatibility'

export default function Landing(){
  return (
    <div className="px-8 py-10 max-w-6xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-6">
          <h1 className="text-4xl font-bold">Predict Insider Threats Before Data Loss Occurs.</h1>
          <p className="text-slate-300">Real-time behavioral analysis and anomaly scoring to stop exfiltration before it happens.</p>
          <DataCompatibility />
        </div>
        <div>
          <LiveSimulator />
        </div>
      </div>
    </div>
  )
}
