import React, { useState, useMemo } from 'react'

export default function DataCompatibility(){
  const [minReqs, setMinReqs] = useState({auth:true,file:true})
  const [enh, setEnh] = useState({email:false,psych:false,usb:false})

  const score = useMemo(()=>{
    let s = 50
    if(minReqs.auth) s += 20
    if(minReqs.file) s += 20
    if(enh.email) s += 5
    if(enh.psych) s += 3
    if(enh.usb) s += 2
    return Math.min(100,s)
  },[minReqs,enh])

  const [remoteStatus, setRemoteStatus] = React.useState(null)

  const testRemote = async () => {
    try{
      const resp = await fetch('http://localhost:8000/api/compatibility', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({user_auth: minReqs.auth, file_access: minReqs.file, email: enh.email, psych: enh.psych, usb: enh.usb})
      })
      const j = await resp.json()
      setRemoteStatus(j)
    }catch(err){
      setRemoteStatus({error: String(err)})
    }
  }

  return (
    <div className="bg-card rounded-lg border border-card-border p-4">
      <h4 className="font-semibold">Will It Work With Your Data?</h4>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
        <div>
          <div className="text-sm font-medium">Minimum Requirements</div>
          <div className="mt-2 space-y-2 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={minReqs.auth} onChange={(e)=>setMinReqs(s => ({...s, auth:e.target.checked}))} />
              <span>User Authentication Logs <span className="text-xs text-slate-400">(Timestamp, IP, Device)</span></span>
            </label>

            <label className="flex items-center gap-2">
              <input type="checkbox" checked={minReqs.file} onChange={(e)=>setMinReqs(s => ({...s, file:e.target.checked}))} />
              <span>File Access Metadata <span className="text-xs text-slate-400">(Open, Read, Delete)</span></span>
            </label>

            <div className="mt-2 text-xs text-slate-500">All PII is hashed & salted (SHA-256)</div>
          </div>
        </div>

        <div>
          <div className="text-sm font-medium">Enhanced Capabilities</div>
          <div className="mt-2 space-y-2 text-sm">
            <label className="flex items-center justify-between">
              <div>
                <div>Email Content Analysis</div>
                <div className="text-xs text-slate-400">Subject lines, Attachment sizes</div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-xs bg-gray-100 px-2 py-1 rounded text-slate-700">AES-256</div>
                <input type="checkbox" checked={enh.email} onChange={(e)=>setEnh(s=>({...s,email:e.target.checked}))} />
              </div>
            </label>

            <label className="flex items-center justify-between">
              <div>
                <div>Psychometric / HR Data</div>
                <div className="text-xs text-slate-400">Performance reviews, Sentiment</div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-xs bg-gray-100 px-2 py-1 rounded text-slate-700">E2E</div>
                <input type="checkbox" checked={enh.psych} onChange={(e)=>setEnh(s=>({...s,psych:e.target.checked}))} />
              </div>
            </label>

            <label className="flex items-center justify-between">
              <div>
                <div>USB Device Logs</div>
                <div className="text-xs text-slate-400">Connection events</div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-xs bg-gray-100 px-2 py-1 rounded text-slate-700">Anon IDs</div>
                <input type="checkbox" checked={enh.usb} onChange={(e)=>setEnh(s=>({...s,usb:e.target.checked}))} />
              </div>
            </label>
          </div>
        </div>
      </div>

      <div className="mt-4">
        <div className="text-xs text-slate-400">Compatibility Score</div>
        <div className="w-full bg-gray-100 rounded h-3 mt-2">
          <div className="h-3 rounded bg-gray-400" style={{width: `${score}%`}} />
        </div>
        <div className="mt-2 text-sm">{score >= 80 ? 'High' : score >= 50 ? 'Moderate' : 'Low'}</div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={testRemote}
            className="px-3 py-2 rounded border border-card-border bg-white text-slate-800 hover:bg-gray-50"
          >
            Test compatibility
          </button>
          {remoteStatus && (
            <div className="text-sm">
              {remoteStatus.error ? (
                <span className="text-red-600">Error: {remoteStatus.error}</span>
              ) : (
                <span className="text-slate-800">Backend: {remoteStatus.score} ({remoteStatus.status})</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
