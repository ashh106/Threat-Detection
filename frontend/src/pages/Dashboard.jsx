import React, { useEffect, useState } from 'react'
import TimelineChart from '../ui/TimelineChart'
import IncidentCard from '../ui/IncidentCard'

export default function Dashboard(){
  const [incidents, setIncidents] = useState([])

  useEffect(()=>{
    const load = async ()=>{
      try{
        const r = await fetch('http://localhost:8000/api/incidents')
        const j = await r.json()
        setIncidents(j)
      }catch(err){
        console.warn('Failed to load incidents', err)
      }
    }
    load()
  },[])

  return (
    <div className="px-8 py-10 max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <div className="bg-card rounded border border-card-border p-4">
          <h3 className="font-semibold">Behavioral Intent Progression (Last 30 Days)</h3>
          <TimelineChart />
        </div>
      </div>

      <div>
        <IncidentCard incidents={incidents} />
      </div>
    </div>
  )
}
