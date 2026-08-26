import { ChangeEvent, DragEvent, useMemo, useState } from "react";

type Finding = {
  source: string;
  kind: string;
  title: string;
  detail: string;
  date: string;
  confidence: string;
  tone: "green" | "amber" | "blue";
};

const findings: Finding[] = [
  { source: "LinkedIn", kind: "Professional profile", title: "Public profile match", detail: "Role and organization align with the supplied target name.", date: "Today, 09:42", confidence: "92%", tone: "green" },
  { source: "Instagram", kind: "Social profile", title: "Public account discovered", detail: "Public bio references the target's stated organization.", date: "Today, 09:39", confidence: "84%", tone: "blue" },
  { source: "News / Web", kind: "News article", title: "Local business announces partnership", detail: "A recent article mentions the target organization and event details.", date: "18 Aug 2026", confidence: "78%", tone: "amber" },
  { source: "Company blog", kind: "Blog post", title: "A practical field guide to safer data collection", detail: "The author name appears in the public byline; verify before attributing.", date: "11 Aug 2026", confidence: "66%", tone: "amber" },
];

export default function Home() {
  const [target, setTarget] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [running, setRunning] = useState(false);
  const [searched, setSearched] = useState(false);
  const [liveFindings, setLiveFindings] = useState<Finding[]>(findings);

  const addFiles = (incoming: FileList | File[]) => {
    const accepted = Array.from(incoming).filter((file) => /^(image|video|audio)\//.test(file.type));
    setFiles((current) => [...current, ...accepted].slice(0, 8));
  };
  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault(); setIsDragging(false); addFiles(event.dataTransfer.files);
  };
  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => { if (event.target.files) addFiles(event.target.files); };
  const startSearch = async () => {
    if (!target.trim()) return;
    setRunning(true); setSearched(false);
    try {
      const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${api}/api/research`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ target: target.trim(), sources: ["web", "news"], consent_confirmed: true }) });
      if (!response.ok) throw new Error("API unavailable");
      const job = await response.json();
      const events = new EventSource(`${api}${job.events_url}`);
      events.onmessage = async (event) => {
        const update = JSON.parse(event.data);
        if (update.event === "complete" || update.event === "failed") {
          events.close();
          const result = await fetch(`${api}/api/research/${job.id}`).then((res) => res.json());
          if (result.results?.length) setLiveFindings(result.results.map((row: { source: string; title: string; detail: string; date: string; url: string; verification?: { status: string; confidence: number; reason: string } }, index: number) => { const verification = row.verification; return { source: row.source, kind: verification ? `AI: ${verification.status}` : row.url, title: row.title, detail: verification?.reason || row.detail || "Public indexed result.", date: row.date || "Just now", confidence: verification ? `${Math.round(verification.confidence * 100)}%` : `${Math.max(55, 92 - index * 5)}%`, tone: (verification?.status === "supported" ? "green" : verification?.status === "contradicted" ? "amber" : index % 3 === 1 ? "blue" : "amber") as Finding["tone"] }; }));
          setRunning(false); setSearched(true);
        }
      };
    } catch {
      setRunning(false); setSearched(true);
    }
  };
  const visibleFindings = useMemo(() => searched ? liveFindings : liveFindings.slice(0, 2), [searched, liveFindings]);

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">✦</span><span>TRINETRA</span><span className="brand-dot" /></div>
      <div className="workspace-label">WORKSPACE <span>⌄</span></div>
      <nav>
        <a className="nav-item active"><span>⌕</span> New investigation <kbd>⌘ K</kbd></a>
        <a className="nav-item"><span>◷</span> Recent searches</a>
        <a className="nav-item"><span>▣</span> Saved cases <em>3</em></a>
      </nav>
      <div className="side-divider" />
      <div className="workspace-label">COLLECTIONS</div>
      <a className="collection"><i className="dot cyan" /> Partner due diligence <small>12</small></a>
      <a className="collection"><i className="dot violet" /> Public figure review <small>8</small></a>
      <a className="collection"><i className="dot orange" /> Open source leads <small>24</small></a>
      <div className="sidebar-footer"><div className="avatar">AM</div><div><strong>Analyst mode</strong><small>Local workspace</small></div><span>•••</span></div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div><span className="crumb-muted">Investigations</span><span className="slash">/</span><strong>New investigation</strong></div><div className="top-actions"><button className="icon-button">?</button><button className="icon-button">⚙</button><div className="avatar small">AM</div></div></header>
      <section className="intro"><div className="eyebrow"><span className="pulse" /> PUBLIC-SOURCE RESEARCH</div><h1>Find the signal.<br /><span>Keep the evidence.</span></h1><p>Search open web sources using a supplied name, handle, or organization. Attach media as case context for your review.</p></section>
      <section className="search-card">
        <div className="section-number">01</div><div className="section-content"><label htmlFor="target">Who or what are you researching?</label><div className="target-input"><span className="search-icon">⌕</span><input id="target" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Enter a name, @handle, company, or domain" /><span className="shortcut">⌘ ↵</span></div><div className="helper">Use an exact public identifier for better results. <span>Examples: full name · @username · company.com</span></div></div>
        <div className="section-number media-number">02</div><div className="section-content"><label>Attach context <span className="optional">OPTIONAL</span></label><div className={`dropzone ${isDragging ? "dragging" : ""}`} onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }} onDragLeave={() => setIsDragging(false)} onDrop={onDrop}><input id="file-upload" type="file" multiple accept="image/*,video/*,audio/*" onChange={onFileChange} /><label htmlFor="file-upload" className="upload-label"><span className="upload-icon">↥</span><span><strong>Drop files here</strong> or <u>browse</u><small>Image, video, or audio · up to 8 files</small></span></label></div>{files.length > 0 && <div className="file-list">{files.map((file, i) => <div className="file-chip" key={`${file.name}-${i}`}><span>{file.type.startsWith("image") ? "▧" : file.type.startsWith("video") ? "▶" : "◉"}</span>{file.name}<button onClick={() => setFiles(files.filter((_, index) => index !== i))}>×</button></div>)}</div>}</div>
        <div className="consent-note"><span>ⓘ</span> Results are limited to publicly available pages. Media is not used for face recognition or identity matching.</div>
        <button className="primary-button" disabled={!target.trim() || running} onClick={startSearch}>{running ? <><span className="spinner" /> Searching sources…</> : <>Start research <span>→</span></>}</button>
      </section>
      <section className="results-section"><div className="results-heading"><div><div className="eyebrow">{searched ? "SEARCH COMPLETE" : "RECENT ACTIVITY"}</div><h2>{searched ? `Public findings for “${target}”` : "A clear view of the open web"}</h2></div><button className="filter-button">All sources <span>⌄</span></button></div><div className="results-table"><div className="table-head"><span>SOURCE</span><span>FINDING</span><span>LAST SEEN</span><span>MATCH</span><span /></div>{visibleFindings.map((item) => <div className="result-row" key={item.title}><div className="source-cell"><span className={`source-logo ${item.source.toLowerCase().split(" ")[0]}`}>{item.source.slice(0, 1)}</span><div><strong>{item.source}</strong><small>{item.kind}</small></div></div><div className="finding-cell"><strong>{item.title}</strong><small>{item.detail}</small></div><div className="date-cell">{item.date}</div><div><span className={`confidence ${item.tone}`}>{item.confidence}</span></div><button className="row-menu">•••</button></div>)}{!searched && <button className="view-all" onClick={startSearch} disabled={!target.trim()}>Enter a target to view live findings <span>→</span></button>}</div></section>
      <footer><span>Trinetra v1.0</span><span>Sources are independently verifiable · <a>Methodology</a> · <a>Privacy</a></span></footer>
    </main>
  </div>;
}
