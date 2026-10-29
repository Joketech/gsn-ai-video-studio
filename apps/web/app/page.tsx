'use client';
import {useEffect, useState, FormEvent} from 'react';

type Row = {id: string; [key: string]: unknown};
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const collections = ['projects', 'scenes', 'characters', 'voices', 'consents', 'assets', 'jobs', 'agent-tasks', 'audit'];

export default function Studio() {
  const [user, setUser] = useState<Row | null>(null);
  const [data, setData] = useState<Record<string, Row[]>>({});
  const [roles, setRoles] = useState<Record<string,string>>({});
  const [tab, setTab] = useState('projects');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  async function api(path: string, body?: unknown, method?: string) {
    const form = body instanceof FormData;
    const r = await fetch(API + path, {method: method || (body ? 'POST' : 'GET'), credentials: 'include',
      headers: body && !form ? {'Content-Type':'application/json'} : {},
      body: body ? (form ? body : JSON.stringify(body)) : undefined});
    if (!r.ok) { const err = await r.json().catch(() => ({})); throw new Error(typeof err.detail === 'string' ? err.detail : `Request failed (${r.status}). Check all fields.`); }
    return r.json();
  }
  async function refresh() {
    const values = await Promise.all(collections.map(c => api('/records/' + c)));
    setData(Object.fromEntries(collections.map((c, i) => [c, values[i]])));
    const agents = await api('/agents'); setRoles(agents.roles);
  }
  useEffect(() => { api('/auth/me').then(u => {setUser(u); return refresh();}).catch(() => {}); }, []); // eslint-disable-line
  useEffect(() => { if (!user) return; const timer = setInterval(() => {refresh().catch(e => setMessage(e.message));}, 5000); return () => clearInterval(timer); }, [user]); // eslint-disable-line
  async function act(action: () => Promise<unknown>, success: string) {
    setBusy(true); setMessage('');
    try {await action(); if(user) await refresh(); setMessage(success);} catch(e) {setMessage(e instanceof Error ? e.message : 'Request failed');} finally {setBusy(false);}
  }
  function fields(e: FormEvent<HTMLFormElement>) { e.preventDefault(); return new FormData(e.currentTarget); }
  function options(name: string, label: string, optional=false) {
    return <label>{label}<select name={name} required={!optional}><option value="">{optional ? 'None' : 'Choose one'}</option>{(data[label.toLowerCase()] || []).map(r => <option key={r.id} value={r.id}>{String(r.name || r.subject || r.id)}</option>)}</select></label>;
  }
  const input = (name: string, label: string, type='text', required=true) => <label>{label}<input name={name} type={type} required={required}/></label>;
  const submit = (label: string) => <button disabled={busy}>{busy ? 'Working…' : label}</button>;
  return <div className="shell"><aside><div className="logo">GSN<span>AI VIDEO STUDIO</span></div><p className="workspace">PRODUCTION WORKSPACE</p><nav>{collections.map(c => <button key={c} className={tab===c?'active':''} onClick={()=>setTab(c)}>{c.replace('-', ' ')}</button>)}</nav><div className="aside-bottom">PHASE 01 <span>Foundation</span><p>Local studio · Cloud ready architecture</p></div></aside>
    <main><header><span>GSN TECHNOLOGY / STUDIO</span>{user && <button onClick={()=>act(async()=>{await api('/auth/logout', {}); setUser(null); setData({});}, 'Signed out')}>Sign out</button>}</header>
    <section className="intro"><div><p className="eyebrow">CREATE WITH INTENTION</p><h1>Your next story<br/><em>starts here.</em></h1><p>Plan scenes. Organize approved identities. Keep production moving.</p></div><div className="mode"><i/> PHASE 1 · SIMULATION<p>Mock Hermes and render adapters.<br/>No AI video or cloned voice is generated.</p></div></section>
    <p className="notice" role="status">{message || 'Private workspace • Consent required for character and voice references'}</p>
    {!user ? <section className="panel auth"><h2>Welcome to your studio</h2><p>Create a workspace or sign in to continue.</p><form onSubmit={e=>{const f=fields(e); const action=(e.nativeEvent as SubmitEvent).submitter?.getAttribute('value'); act(async()=>{const body=Object.fromEntries(f); if(action==='register') await api('/auth/register',body); await api('/auth/login',body); setUser(await api('/auth/me')); await refresh();}, 'Welcome to GSN Studio');}}>{input('email','Email','email')}{input('password','Password (at least 12 characters)','password')}{input('workspace','Workspace name')}<div className="actions"><button disabled={busy} value="login">Sign in</button><button disabled={busy} value="register" className="secondary">Create workspace</button></div></form></section> : <>
    <div className="stats">{[['projects','Projects'],['scenes','Scenes'],['characters','Characters'],['jobs','Render jobs']].map(([c,l])=><div key={c}><span>{l}</span><strong>{(data[c]||[]).length.toString().padStart(2,'0')}</strong></div>)}</div>
    <section className="content"><div className="panel"><p className="eyebrow">WORKSPACE</p><h2>{tab.replace('-', ' ')}</h2>
    {tab==='projects' && <form onSubmit={e=>{const f=fields(e); act(()=>api('/projects',Object.fromEntries(f)),'Project created');}}>{input('name','Project name')}<label>Production brief<textarea name="brief"/></label>{submit('Create project')}</form>}
    {tab==='assets' && <form onSubmit={e=>{const f=fields(e); act(()=>api('/assets',f),'Reference uploaded');}}><p>Upload consent evidence, photographs or voice samples. Maximum 20 MB.</p><input aria-label="Reference file" type="file" name="file" accept="image/jpeg,image/png,audio/wav,audio/mpeg,application/pdf" required/>{submit('Upload reference')}</form>}
    {tab==='consents' && <form onSubmit={e=>{const f=fields(e); act(()=>api('/consents',{subject:f.get('subject'),scope:f.get('scope'),evidence_asset_id:f.get('evidence_asset_id'),expires_at:new Date(String(f.get('expires_at'))).toISOString(),commercial_use:f.has('commercial_use'),attestation:f.has('attestation')}),'Consent recorded');}}>{input('subject','Person granting consent')}<label>Permission scope<select name="scope"><option value="appearance">Appearance</option><option value="voice">Voice</option></select></label>{options('evidence_asset_id','Assets')}{input('expires_at','Expires at','datetime-local')}<label className="check"><input type="checkbox" name="commercial_use"/>Commercial use authorized</label><label className="check"><input required type="checkbox" name="attestation"/>I have permission and have uploaded evidence.</label>{submit('Record consent')}<p>Recording evidence does not independently verify a person’s identity.</p></form>}
    {(tab==='characters'||tab==='voices') && <form onSubmit={e=>{const f=fields(e); act(()=>api('/profiles/'+(tab==='characters'?'character':'voice'),{name:f.get('name'),consent_id:f.get('consent_id'),reference_asset_ids:[f.get('reference')]}),'Profile created');}}>{input('name','Profile name')}{options('consent_id','Consents')}{options('reference','Assets')}{submit('Save reusable profile')}</form>}
    {tab==='scenes' && <form onSubmit={e=>{const f=fields(e); act(()=>api('/scenes',{project_id:f.get('project_id'),script:f.get('script'),setting:f.get('setting'),camera:f.get('camera'),seconds:Number(f.get('seconds')),character_id:f.get('character_id')||null,voice_id:f.get('voice_id')||null,commercial:f.has('commercial')}),'Scene created');}}>{options('project_id','Projects')}<label>Script<textarea name="script" required/></label>{input('setting','Setting','text',false)}<label>Camera<select name="camera">{['static','pan','dolly','orbit'].map(x=><option key={x}>{x}</option>)}</select></label><label>Seconds<input type="number" name="seconds" min="1" max="30" defaultValue="5" required/></label>{options('character_id','Characters',true)}{options('voice_id','Voices',true)}<label className="check"><input type="checkbox" name="commercial"/>Commercial production</label>{submit('Add scene')}</form>}
    {tab==='jobs' && <form onSubmit={e=>{const f=fields(e); act(()=>api('/renders',{scene_id:f.get('scene_id'),request_key:crypto.randomUUID()}),'Render simulation queued');}}>{options('scene_id','Scenes')}<p>The worker writes a JSON simulation report. GPU generation is not connected.</p>{submit('Queue simulation')}</form>}
    {tab==='agent-tasks' && <form onSubmit={e=>{const f=fields(e); act(()=>api('/agent-tasks',Object.fromEntries(f)),'Simulated task recorded');}}>{options('project_id','Projects')}<label>Specialist<select name="role">{Object.entries(roles).map(([k,v])=><option key={k} value={k}>{k} — {v}</option>)}</select></label><label>Instruction<textarea required name="instruction"/></label>{submit('Assign mock task')}</form>}
    {tab==='audit' && <p>Read-only activity history for this workspace. The application records account, consent and production actions.</p>}
    </div><div className="panel records"><div className="section-title"><h2>Workspace records</h2><button className="secondary" onClick={()=>act(refresh,'Updated')}>Refresh</button></div>{!(data[tab]||[]).length && <div className="empty"><span>＋</span><h3>A blank canvas</h3><p>Your {tab.replace('-',' ')} will appear here.</p></div>}{(data[tab]||[]).map(r=><article key={r.id}><h3>{String(r.name||r.subject||r.action||r.status||'Record')}</h3><code>{r.id}</code><details><summary>View details</summary><pre>{JSON.stringify(r,null,2)}</pre></details>{tab==='consents' && !r.revoked && <button className="secondary" onClick={()=>act(()=>api('/consents/'+r.id+'/revoke',{}),'Consent revoked')}>Revoke consent</button>}{tab==='assets' && <a href={API+'/assets/'+r.id+'/content'}>Download asset</a>}{tab==='jobs' && Boolean(r.output_asset_id) && <a href={API+'/assets/'+r.output_asset_id+'/content'}>Download simulation report</a>}</article>)}</div></section></>}
    <footer>GSN AI Video Studio <span>Built for a deliberate production process.</span></footer></main></div>;
}
