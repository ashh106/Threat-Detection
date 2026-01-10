import React, { useEffect, useState, useMemo } from 'react'
import IncidentCard from '../ui/IncidentCard'
import { Shield, FileText, AlertTriangle, Ban, UserX } from 'lucide-react'

export default function Dashboard(){
  const [incidents, setIncidents] = useState([])
  const [anomalies, setAnomalies] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(()=>{
    const load = async ()=>{
      try{
        setError(null)
        const [incRes, anomRes] = await Promise.all([
          fetch('http://localhost:8000/api/incidents'),
          fetch('http://localhost:8000/api/anomalies?limit=200')
        ])

        const incJson = await incRes.json()
        const anomJson = await anomRes.json()
        setIncidents(Array.isArray(incJson) ? incJson : [])
        setAnomalies(Array.isArray(anomJson) ? anomJson : [])
        if(Array.isArray(anomJson) && anomJson.length > 0){
          setSelected(anomJson[0])
        }
      }catch(err){
        console.warn('Failed to load dashboard data', err)
        setError('Failed to load data from backend')
      }finally{
        setLoading(false)
      }
    }
    load()
  },[])

  const summary = useMemo(()=>{
    if(!anomalies || anomalies.length === 0) return { total:0, high:0, avg:0 }
    const total = anomalies.length
    const high = anomalies.filter(a => a.severity === 'HIGH' || a.severity === 'CRITICAL').length
    const avg = anomalies.reduce((acc,a)=> acc + (a.anomaly_score || 0), 0) / total
    return { total, high, avg }
  },[anomalies])

  const handleRestrictFileAccess = async () => {
    if (!selected) return
    setActionLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/restrict-access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user: selected.user,
          date: selected.date,
          action: 'restrict_file_access'
        })
      })
      const result = await response.json()
      if (response.ok) {
        alert(`File access restricted for user ${selected.user}`)
        // Refresh incidents to show new incident
        const incRes = await fetch('http://localhost:8000/api/incidents')
        const incJson = await incRes.json()
        setIncidents(Array.isArray(incJson) ? incJson : [])
      } else {
        alert('Failed to restrict access: ' + result.error)
      }
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setActionLoading(false)
    }
  }

  const handleSuspendUser = async () => {
    if (!selected) return
    setActionLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/suspend-user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user: selected.user,
          date: selected.date,
          action: 'suspend_user'
        })
      })
      const result = await response.json()
      if (response.ok) {
        alert(`User ${selected.user} suspended successfully`)
        // Refresh incidents
        const incRes = await fetch('http://localhost:8000/api/incidents')
        const incJson = await incRes.json()
        setIncidents(Array.isArray(incJson) ? incJson : [])
      } else {
        alert('Failed to suspend user: ' + result.error)
      }
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="px-8 py-10 max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card rounded border border-card-border p-4">
          <div className="text-xs text-slate-400">Total Scored Days</div>
          <div className="text-2xl font-semibold mt-1">{summary.total}</div>
        </div>
        <div className="bg-card rounded border border-card-border p-4">
          <div className="text-xs text-slate-400">High / Critical Anomalies</div>
          <div className="text-2xl font-semibold mt-1">{summary.high}</div>
        </div>
        <div className="bg-card rounded border border-card-border p-4">
          <div className="text-xs text-slate-400">Average Anomaly Score</div>
          <div className="text-2xl font-semibold mt-1">{summary.avg.toFixed(2)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-card rounded border border-card-border p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">Behavioral Anomalies</h3>
              {loading && <div className="text-xs text-slate-400">Loading...</div>}
              {error && !loading && <div className="text-xs text-rose-400">{error}</div>}
            </div>

            <div className="overflow-x-auto text-xs">
              <table className="w-full border-collapse min-w-[520px]">
                <thead>
                  <tr className="text-slate-300 border-b border-card-border">
                    <th className="text-left py-2 pr-2">User</th>
                    <th className="text-left py-2 px-2">Date</th>
                    <th className="text-left py-2 px-2">Score</th>
                    <th className="text-left py-2 px-2">Severity</th>
                    <th className="text-left py-2 px-2">Top Feature</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.length === 0 && !loading ? (
                    <tr>
                      <td colSpan={5} className="py-4 text-center text-slate-500">No anomaly scores available. Run training + inference.</td>
                    </tr>
                  ) : (
                    anomalies.map((a,idx)=>{
                      const isSelected = selected && selected.user === a.user && selected.date === a.date
                      const sev = a.severity || 'UNKNOWN'
                      const sevColor = sev === 'CRITICAL' ? 'bg-gray-300 text-slate-800' : sev === 'HIGH' ? 'bg-gray-200 text-slate-800' : 'bg-gray-100 text-slate-700'
                      return (
                        <tr
                          key={idx}
                          onClick={()=>setSelected(a)}
                          className={
                            'cursor-pointer hover:bg-gray-100 ' +
                            (isSelected ? 'bg-gray-200' : '')
                          }
                        >
                          <td className="py-2 pr-2 font-mono text-xs text-slate-900">{a.user}</td>
                          <td className="py-2 px-2 text-slate-800">{a.date}</td>
                          <td className="py-2 px-2">{(a.anomaly_score || 0).toFixed(2)}</td>
                          <td className="py-2 px-2">
                            <span className={"px-2 py-0.5 rounded-full text-[10px] " + sevColor}>{sev}</span>
                          </td>
                          <td className="py-2 px-2 text-slate-800">{a.top_feature || '-'}</td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <IncidentCard incidents={incidents} />

          <div className="bg-card rounded border border-card-border p-4 text-xs">
            <div className="font-semibold mb-3 flex items-center gap-2">
              <AlertTriangle className="text-rose-400" />
              Anomaly Details & Actions
            </div>
            {!selected ? (
              <div className="text-slate-400">Click a row to view model explanation and take action.</div>
            ) : (
              <div className="space-y-3">
                {/* User Information */}
                <div className="bg-gray-50 p-2 rounded border border-card-border/60">
                  <div className="font-semibold text-slate-800 mb-1">User Information</div>
                  <div className="text-slate-700">User: <span className="font-mono">{selected.user}</span></div>
                  <div className="text-slate-700">Date: {selected.date}</div>
                  <div className="text-slate-700">Score: {(selected.anomaly_score || 0).toFixed(2)}</div>
                  <div className="text-slate-700">Severity: <span className={`px-2 py-0.5 rounded-full text-[10px] ${
                    selected.severity === 'CRITICAL' ? 'bg-gray-300 text-slate-800' : 
                    selected.severity === 'HIGH' ? 'bg-gray-200 text-slate-800' : 
                    'bg-gray-100 text-slate-700'
                  }`}>{selected.severity}</span></div>
                </div>

                {/* Activity Details */}
                <div className="bg-gray-50 p-2 rounded border border-card-border/60">
                  <div className="font-semibold text-slate-800 mb-1 flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    Activity Details
                  </div>
                  <div className="text-slate-700">Top Feature: {selected.top_feature || 'N/A'}</div>
                  <div className="text-slate-700">Risk Level: {
                    (selected.anomaly_score || 0) > 0.8 ? 'Critical' :
                    (selected.anomaly_score || 0) > 0.6 ? 'High' :
                    (selected.anomaly_score || 0) > 0.4 ? 'Medium' : 'Low'
                  }</div>
                  <div className="text-slate-700 mt-2 text-xs whitespace-pre-wrap">{selected.explanation || 'No explanation provided.'}</div>
                </div>

                {/* Model Explainability */}
                <div className="bg-blue-50 p-2 rounded border border-blue-200">
                  <div className="font-semibold text-slate-800 mb-1 flex items-center gap-1">
                    <Shield className="w-3 h-3 text-blue-600" />
                    Model Explainability
                  </div>
                  <div className="text-slate-700 text-xs">
                    This anomaly was flagged due to unusual behavioral patterns detected by our ML model. 
                    The system analyzed multiple features including access patterns, timing anomalies, 
                    and deviation from established user baselines.
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="space-y-2 pt-2">
                  <div className="font-semibold text-slate-800 mb-2">Security Actions</div>
                  
                  <button
                    onClick={handleRestrictFileAccess}
                    disabled={actionLoading}
                    className="w-full px-3 py-2 rounded border border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-xs"
                  >
                    <Ban className="w-3 h-3" />
                    {actionLoading ? 'Processing...' : 'Restrict File Access'}
                  </button>

                  <button
                    onClick={handleSuspendUser}
                    disabled={actionLoading}
                    className="w-full px-3 py-2 rounded border border-red-200 bg-red-50 text-red-800 hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-xs"
                  >
                    <UserX className="w-3 h-3" />
                    {actionLoading ? 'Processing...' : 'Suspend User Account'}
                  </button>

                  <div className="text-xs text-slate-500 text-center pt-1">
                    Actions will create security incidents and notify administrators
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
