import { useEffect, useRef, useState } from "react";

import type { AskResponse, Citation, DocumentInfo } from "./api";
import { askQuestion, fetchDocuments, uploadDocument } from "./api";

type IconName = "document" | "layers" | "plus" | "arrow" | "sparkle" | "clock" | "chart" | "leaf" | "flag" | "check";

function Icon({ name, className = "" }: { name: IconName; className?: string }) {
  const shapes = {
    document: <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z" /><path d="M14 3v6h6M8 13h8M8 17h5" /></>,
    layers: <><rect x="8" y="3" width="12" height="15" rx="2" /><path d="M16 21H6a2 2 0 0 1-2-2V8M12 8h4M12 12h4" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
    sparkle: <><path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4Z" /><path d="M20 3v4M18 5h4" /></>,
    clock: <><circle cx="12" cy="12" r="8" /><path d="M12 8v4l3 2" /></>,
    chart: <path d="M4 4v16h16M8 15v-4M12 15V7M16 15v-6" />,
    leaf: <><path d="M20 4c-7-1-15 1-15 8a7 7 0 0 0 7 7c7 0 9-8 8-15Z" /><path d="M4 21 15 10M8 17v-5M8 17h5" /></>,
    flag: <path d="M5 21V4m0 1c5-4 9 4 14 0v10c-5 4-9-4-14 0" />,
    check: <path d="m5 12 4 4L19 6" />,
  };
  return (
    <svg className={"icon " + className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {shapes[name]}
    </svg>
  );
}

const EXAMPLE_QUESTIONS: { label: string; icon: IconName; question: string }[] = [
  { label: "Operations", icon: "chart", question: "What was the first time fix rate in Q3?" },
  { label: "Sustainability", icon: "leaf", question: "How much were Scope 2 emissions?" },
  { label: "Project delivery", icon: "flag", question: "When is Project Beacon going live and what is the main risk?" },
];

function documentTitle(filename: string) {
  const title = filename.replace(/\.(pdf|md|markdown|txt)$/i, "").replace(/[-_]+/g, " ");
  return title.charAt(0).toUpperCase() + title.slice(1);
}

function documentType(filename: string) {
  const extension = filename.split(".").pop()?.toLowerCase();
  return extension === "md" || extension === "markdown" ? "Markdown" : extension === "pdf" ? "PDF" : "Text";
}

function renderAnswer(answer: string, onCitation: (ref: number) => void) {
  return answer.split(/(\[\d+\])/g).map((part, i) => {
    const match = /^\[(\d+)\]$/.exec(part);
    if (!match) return <span key={i}>{part}</span>;
    const ref = Number(match[1]);
    return <button key={i} type="button" className="cite-chip" onClick={() => onCitation(ref)} aria-label={"Go to source " + ref}>{ref}</button>;
  });
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [connection, setConnection] = useState<"loading" | "ready" | "offline">("loading");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [activeRef, setActiveRef] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const citationRefs = useRef<Record<number, HTMLLIElement | null>>({});
  const canAsk = connection === "ready" && documents.length > 0 && !busy && !uploading;
  const shortcutKey = /Mac|iPhone|iPad/.test(navigator.userAgent) ? "⌘" : "Ctrl";

  useEffect(() => {
    fetchDocuments()
      .then((items) => { setDocuments(items); setConnection("ready"); })
      .catch(() => setConnection("offline"));
  }, []);

  async function handleAsk(text: string) {
    if (text.trim().length < 3 || !canAsk) return;
    setBusy(true);
    setError(null);
    setResult(null);
    setActiveRef(null);
    try {
      setResult(await askQuestion(text.trim()));
    } catch {
      setError("We couldn’t get an answer. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(file: File | undefined) {
    if (!file || uploading || busy) return;
    setUploading(true);
    setDragging(false);
    setUploadError(null);
    try {
      await uploadDocument(file);
      setDocuments(await fetchDocuments());
      setConnection("ready");
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "We couldn’t add that document. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  function jumpToCitation(ref: number) {
    setActiveRef(ref);
    const source = citationRefs.current[ref];
    source?.focus({ preventScroll: true });
    source?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "center",
    });
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace">Skip to workspace</a>
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark"><Icon name="layers" /></span>
          <div className="brand-copy"><span className="brand-name">Report Assistant</span><span className="brand-subtitle">Document intelligence</span></div>
        </div>
        <div className="header-context">
          <span className="workspace-label">Your workspace</span>
          <span className={"connection-status connection-" + connection} role="status">
            <span className="status-dot" />{connection === "ready" ? "Connected" : connection === "loading" ? "Connecting" : "Offline"}
          </span>
        </div>
      </header>

      <aside className="sidebar" aria-label="Document library">
        <div className="library">
          <div className="section-heading library-heading"><h2>Documents</h2><span className="count-badge" aria-label={documents.length + " documents"}>{documents.length}</span></div>
          <p className="library-description">The sources behind your answers.</p>
          {connection === "loading" ? (
            <div className="document-loading" role="status"><span className="skeleton" /><span className="skeleton" /><span className="skeleton" /><span className="sr-only">Loading documents</span></div>
          ) : documents.length === 0 ? (
            <p className="library-empty">{connection === "offline" ? "Your documents are currently unavailable." : "Add your first document to get started."}</p>
          ) : (
            <ul className="document-list">
              {documents.map((doc) => (
                <li key={doc.name} className="document-item" title={doc.name}>
                  <span className="document-icon"><Icon name="document" /></span>
                  <div className="document-details">
                    <span className="document-name">{documentTitle(doc.name)}</span>
                    <span className="document-meta">{documentType(doc.name)}<span aria-hidden="true"> · </span>{doc.chunks} {doc.chunks === 1 ? "passage" : "passages"}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div
            className={"upload-area" + (dragging ? " is-dragging" : "")}
            onDragOver={(event) => { event.preventDefault(); if (!uploading && !busy) setDragging(true); }}
            onDragLeave={(event) => { if (!(event.relatedTarget instanceof Node) || !event.currentTarget.contains(event.relatedTarget)) setDragging(false); }}
            onDrop={(event) => { event.preventDefault(); setDragging(false); void handleUpload(event.dataTransfer.files[0]); }}
          >
            <button type="button" className="upload-button" onClick={() => fileInput.current?.click()} disabled={uploading || busy}>
              <span className="upload-symbol">{uploading ? <span className="spinner" /> : <Icon name="plus" />}</span>
              <span className="upload-copy"><span className="upload-title">{uploading ? "Adding document…" : dragging ? "Drop your document" : "Add a document"}</span><span className="upload-caption">PDF, Markdown, or text</span></span>
            </button>
            <input ref={fileInput} className="sr-only" type="file" accept=".pdf,.md,.markdown,.txt" tabIndex={-1} aria-label="Choose a document to upload" disabled={uploading || busy} onChange={(event) => { void handleUpload(event.target.files?.[0]); event.target.value = ""; }} />
          </div>
          {uploadError && <p className="error-message upload-error" role="alert">{uploadError}</p>}
          <p className="upload-hint" role="status">{uploading ? "Preparing your document for questions." : "Or drag a file here to add it."}</p>
        </div>
        <div className="session-note"><Icon name="clock" /><div><p>Temporary workspace</p><span>Uploaded documents are cleared when the server restarts.</span></div></div>
      </aside>

      <main id="workspace" className="workspace" tabIndex={-1}>
        <div className="workspace-content">
          <div className="page-heading">
            <div className="eyebrow"><span /> REPORT WORKSPACE</div>
            <h1>Your reports.<br /><span>Clearer answers.</span></h1>
            <p>Find the detail you need, with the sources to back it up.</p>
          </div>
          {connection === "offline" && <p className="error-message connection-error" role="alert">The document service is unavailable. Start the backend, then refresh this page to reconnect.</p>}
          <form className="composer" onSubmit={(event) => { event.preventDefault(); void handleAsk(question); }} aria-busy={busy}>
            <label className="composer-label" htmlFor="question"><Icon name="sparkle" />Ask your documents</label>
            <textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); void handleAsk(question); } }}
              placeholder="What would you like to know?" rows={3} maxLength={10000} aria-describedby="question-hint" />
            <div className="composer-footer">
              <span id="question-hint" className="composer-hint"><Icon name="document" />Answers linked to your sources</span>
              <div className="composer-actions">
                <span className="keyboard-hint" aria-hidden="true">{shortcutKey} ↵</span>
                <button className="ask-button" type="submit" disabled={!canAsk || question.trim().length < 3}>{busy ? <><span className="spinner" />Searching</> : <>Ask question<Icon name="arrow" /></>}</button>
              </div>
            </div>
          </form>
          {error && <p className="error-message question-error" role="alert">{error}</p>}
          {!result && !busy && (
            <section className="suggestions" aria-labelledby="suggestions-title">
              <div className="section-heading suggestions-heading"><h2 id="suggestions-title">A place to start</h2><span>Explore the sample reports</span></div>
              <div className="suggestion-grid">
                {EXAMPLE_QUESTIONS.map((example) => (
                  <button key={example.label} type="button" className="suggestion-card" disabled={!canAsk} onClick={() => { setQuestion(example.question); void handleAsk(example.question); }}>
                    <span className={"suggestion-icon suggestion-" + example.icon}><Icon name={example.icon} /></span>
                    <span className="suggestion-label">{example.label}</span><span className="suggestion-question">{example.question}</span><Icon name="arrow" className="suggestion-arrow" />
                  </button>
                ))}
              </div>
            </section>
          )}
          <div className="response-region" aria-live="polite" aria-atomic="true">
            {busy && <div className="answer-loading" role="status"><div className="loading-heading"><span className="spinner" />Finding the relevant passages…</div><span className="skeleton" /><span className="skeleton" /><span className="skeleton" /></div>}
            {result && (
              <section className="answer-panel" aria-labelledby="answer-title">
                <div className="section-heading answer-heading">
                  <h2 id="answer-title"><span className="answer-icon"><Icon name="check" /></span>Your answer</h2>
                  <span className="answer-mode">{result.mode === "azure-openai" ? "AI generated" : "From your documents"}</span>
                </div>
                <p className="answer-text">{renderAnswer(result.answer, jumpToCitation)}</p>
                {result.citations.length > 0 && (
                  <div className="sources">
                    <div className="section-heading sources-heading"><h3>Sources</h3><span>{result.citations.length} {result.citations.length === 1 ? "reference" : "references"}</span></div>
                    <ol className="citation-list">
                      {result.citations.map((citation: Citation) => (
                        <li key={citation.ref} ref={(el) => { citationRefs.current[citation.ref] = el; }} className={"citation-card" + (activeRef === citation.ref ? " is-active" : "")} tabIndex={-1} aria-label={"Source " + citation.ref + ": " + citation.document}>
                          <span className="source-number" aria-hidden="true">{citation.ref}</span>
                          <div className="source-content">
                            <div className="source-heading"><strong>{documentTitle(citation.document)}</strong><span>Passage {citation.chunk_id.match(/#chunk-(\d+)$/)?.[1] ?? citation.ref}</span></div>
                            <span className="source-filename">{citation.document}</span><p>{citation.excerpt}{citation.excerpt.length >= 280 ? "…" : ""}</p>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </section>
            )}
          </div>
          <footer className="workspace-footer"><Icon name="layers" /><span>Built for answers you can trace.<span className="footer-divider" aria-hidden="true"> · </span><span className="sample-disclaimer">Sample reports are fictional.</span></span></footer>
        </div>
      </main>
    </div>
  );
}
