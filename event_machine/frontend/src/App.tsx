import { lazy, Suspense, useEffect, useMemo, useState } from "react"
import Papa from "papaparse"
import { toast } from "sonner"
import {
  ArrowDownToLine, ArrowLeft, ArrowRight, ArrowUpRight, Check, ChevronRight,
  CircleHelp, CloudUpload, Database, FileCheck2, FileSpreadsheet,
  Filter, Link2, LoaderCircle, LockKeyhole, Search, ShieldCheck, Sparkles, Upload,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

const EventMarkdown = lazy(() => import("@/components/EventMarkdown"))

type View = "overview" | "prepare" | "results" | "clay"
type Counts = { participants: number; accounts: number; matches: number; match_statuses: Record<string, number>; event_pages: number; research_errors: number }
type Manifest = { event_id: string; event_name?: string; event_date?: string; as_of: string; counts: Counts; client_counts: Record<string, Record<string, number>>; inputs?: Record<string, { path: string; sha256: string }> }
type Run = { run_id: string; manifest: Manifest; files: string[] }
type Match = Record<string, string> & { match_key: string; person_name: string; company_name: string; client_id: string; client_name: string; fit_status: string; machine_status: string; priority_score: string }
type AgentReceipt = { artifact_sha256: string; candidates: number; candidate_url: string; status: string }
type EventForm = { id: string; name: string; edition: string; date: string; url: string; registration_marker: string }
type InputKey = "participants" | "accounts" | "relations" | "evidence"

const EMPTY_EVENT: EventForm = { id: "", name: "", edition: "", date: "", url: "", registration_marker: "" }
const OUTPUT_NAMES: Record<string, string> = {
  "matches.csv": "Matchs ICP", "review-queue.csv": "File de revue", "participants.csv": "Participants qualifiés",
  "accounts.csv": "Entreprises rapprochées", "event-brief.md": "Contexte de l’événement",
  "agent-handoff.md": "Mission des agents Codex",
  "clay-import-all.csv": "Import Clay · tous les matchs", "clay-import-priority.csv": "Import Clay · pistes prioritaires",
  "feedback-template.csv": "Modèle de corrections", "evidence.csv": "Preuves et signaux",
  "event-pages.json": "Pages consultées", "research-errors.json": "Erreurs de recherche",
  "run-manifest.json": "Manifeste du calcul",
}
const FILES: { key: InputKey; title: string; note: string; required?: boolean }[] = [
  { key: "participants", title: "Participants", note: "Liste d’inscrits ou de contacts fournie", required: true },
  { key: "accounts", title: "Entreprises", note: "Domaines, secteurs et attributs connus" },
  { key: "relations", title: "Relations existantes", note: "Comptes ou contacts déjà suivis" },
  { key: "evidence", title: "Preuves et signaux", note: "Sources vérifiées par entreprise" },
]
const statusLabels: Record<string, string> = { "fort": "Fort", "possible": "Possible", "à confirmer": "À confirmer", "exclu": "Exclu" }
const statusColors: Record<string, "signal" | "outline" | "muted" | "danger"> = { "fort": "signal", "possible": "signal", "à confirmer": "outline", "exclu": "danger" }

async function getJSON<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" })
  if (!response.ok) throw new Error(response.status === 404 ? "Aucune analyse précédente" : `Erreur ${response.status}`)
  return response.json() as Promise<T>
}
async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
  let data: Record<string, unknown> = {}
  try { data = await response.json() } catch { /* server unavailable */ }
  if (!response.ok) throw new Error(String(data.error || `Erreur ${response.status}`))
  return data as T
}
function download(runId: string, file: string) { return `/runs/${runId}/${file}` }
function formatNumber(value: number | undefined) { return new Intl.NumberFormat("fr-CA").format(value || 0) }
function statusBase(value: string) { return value.replace(" (revue humaine)", "") }
function fitBadge(status: string) {
  const key = statusBase(status)
  return <Badge variant={statusColors[key] || "muted"}>{statusLabels[key] || key}{status.includes("revue humaine") ? " · revu" : ""}</Badge>
}
function niceError(error: unknown) { return error instanceof Error ? error.message : "Une erreur est survenue" }
function splitPipe(value: string) { return (value || "").split(" | ").map(x => x.trim()).filter(Boolean) }

function FileDrop({ title, note, required, value, onChange }: { title: string; note: string; required?: boolean; value: File | null; onChange: (file: File | null) => void }) {
  return <label className="file-drop" data-filled={!!value}>
    <span className="flex items-start justify-between gap-3"><span className="file-drop-title">{title} {required && <span className="text-[#85857c]">*</span>}</span>{value ? <FileCheck2 size={17} className="text-[#65752d]" /> : <CloudUpload size={18} className="text-[#8b8b80]" />}</span>
    <span className="file-drop-note">{value ? `${value.name} · ${(value.size / 1024).toFixed(0)} Ko` : note}</span>
    <input type="file" accept=".csv,text/csv" aria-label={`Importer ${title}`} onChange={event => onChange(event.target.files?.[0] || null)} />
  </label>
}

function SectionHeading({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return <div className="section-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>
}

function App() {
  const [view, setView] = useState<View>("overview")
  const [run, setRun] = useState<Run | null>(null)
  const [loadingLatest, setLoadingLatest] = useState(true)
  const [loadingOutputs, setLoadingOutputs] = useState(false)
  const [matches, setMatches] = useState<Match[]>([])
  const [brief, setBrief] = useState("")
  const [eventForm, setEventForm] = useState<EventForm>(EMPTY_EVENT)
  const [eventExtra, setEventExtra] = useState<Record<string, unknown>>({})
  const [icpJson, setIcpJson] = useState("")
  const [uploads, setUploads] = useState<Record<InputKey, File | null>>({ participants: null, accounts: null, relations: null, evidence: null })
  const [offline, setOffline] = useState(false)
  const [running, setRunning] = useState(false)
  const [selected, setSelected] = useState<Match | null>(null)
  const [clientFilter, setClientFilter] = useState("all")
  const [statusFilter, setStatusFilter] = useState("priority")
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(0)
  const [feedbackFile, setFeedbackFile] = useState<File | null>(null)
  const [feedbackBusy, setFeedbackBusy] = useState(false)
  const [agentArtifactFile, setAgentArtifactFile] = useState<File | null>(null)
  const [agentReceipt, setAgentReceipt] = useState<AgentReceipt | null>(null)
  const [agentBusy, setAgentBusy] = useState(false)
  useEffect(() => {
    getJSON<Run>("/api/runs/latest").then(setRun).catch(() => {}).finally(() => setLoadingLatest(false))
  }, [])
  useEffect(() => {
    if (!run) { setMatches([]); setBrief(""); return }
    let cancelled = false
    setLoadingOutputs(true)
    Promise.all([
      fetch(download(run.run_id, "matches.csv")).then(response => { if (!response.ok) throw new Error("Matchs indisponibles"); return response.text() }),
      fetch(download(run.run_id, "event-brief.md")).then(response => response.ok ? response.text() : ""),
    ]).then(([csvText, eventText]) => {
      if (cancelled) return
      const parsed = Papa.parse<Match>(csvText, { header: true, skipEmptyLines: true })
      setMatches(parsed.data)
      setBrief(eventText)
    }).catch(error => { if (!cancelled) toast.error(niceError(error)) }).finally(() => { if (!cancelled) setLoadingOutputs(false) })
    return () => { cancelled = true }
  }, [run])

  const icpNames = useMemo(() => {
    try {
      const json = JSON.parse(icpJson) as { clients?: { id?: string; name?: string }[] }
      return Array.isArray(json.clients) ? json.clients.map(client => client.name || client.id || "Profil sans nom") : []
    } catch { return [] }
  }, [icpJson])
  const clientOptions = useMemo(() => [...new Map(matches.map(row => [row.client_id, row.client_name])).entries()], [matches])
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("fr-CA")
    return matches.filter(row => {
      const status = statusBase(row.fit_status)
      return (clientFilter === "all" || row.client_id === clientFilter) &&
        (statusFilter === "all" || statusFilter === "priority" && status !== "exclu" || status === statusFilter) &&
        (!query || [row.person_name, row.company_name, row.job_title, row.client_name].some(value => (value || "").toLocaleLowerCase("fr-CA").includes(query)))
    }).sort((a, b) => Number(b.priority_score) - Number(a.priority_score))
  }, [matches, clientFilter, statusFilter, search])
  const visible = filtered.slice(page * 25, (page + 1) * 25)
  useEffect(() => setPage(0), [clientFilter, statusFilter, search])

  function setUpload(key: InputKey, file: File | null) {
    if (file && !file.name.toLowerCase().endsWith(".csv")) { toast.error("Sélectionnez un fichier CSV"); return }
    setUploads(previous => ({ ...previous, [key]: file }))
  }
  async function loadHopExample() {
    try {
      const [event, profiles] = await Promise.all([
        getJSON<Record<string, unknown>>("/examples/hop-2026-event.json"),
        getJSON<Record<string, unknown>>("/examples/hop-2026-icps.json"),
      ])
      const { id, name, edition, date, url, registration_marker, ...extra } = event
      setEventForm({ id: String(id || ""), name: String(name || ""), edition: String(edition || ""), date: String(date || ""), url: String(url || ""), registration_marker: String(registration_marker || "") })
      setEventExtra(extra)
      setIcpJson(JSON.stringify(profiles, null, 2))
      setOffline(true)
      toast.success("Exemple HOP et trois profils ICP chargés")
    } catch (error) { toast.error(niceError(error)) }
  }
  async function importIcp(file: File | null) {
    if (!file) return
    try {
      const text = await file.text()
      const parsed = JSON.parse(text)
      if (!Array.isArray(parsed.clients) || !parsed.clients.length) throw new Error("Le JSON doit contenir un tableau clients non vide")
      setIcpJson(JSON.stringify(parsed, null, 2))
      toast.success(`${parsed.clients.length} profils ICP chargés`)
    } catch (error) { toast.error(niceError(error)) }
  }
  async function runAnalysis() {
    if (!eventForm.id.trim() || !eventForm.name.trim()) { toast.error("Ajoutez le nom et l’identifiant de l’événement"); return }
    if (!uploads.participants) { toast.error("Importez la liste des participants"); return }
    if (!icpNames.length) { toast.error("Importez au moins un profil ICP valide"); return }
    const totalBytes = Object.values(uploads).reduce((sum, file) => sum + (file?.size || 0), 0)
    if (totalBytes > 18_000_000) { toast.error("Les CSV dépassent la limite de 18 Mo de cette interface"); return }
    setRunning(true)
    try {
      const inputs: Record<string, string> = {}
      await Promise.all((Object.entries(uploads) as [InputKey, File | null][]).map(async ([key, file]) => { inputs[key] = file ? await file.text() : "" }))
      const event = { ...eventExtra, ...Object.fromEntries(Object.entries(eventForm).map(([key, value]) => [key, value.trim()])) }
      const result = await postJSON<Run>("/api/run", { event, icps: JSON.parse(icpJson), inputs, offline })
      setRun(result)
      setClientFilter("all"); setStatusFilter("priority"); setSearch("")
      setAgentReceipt(null)
      setView("results")
      toast.success(`Analyse terminée : ${formatNumber(result.manifest.counts.matches)} évaluations`)
    } catch (error) { toast.error(niceError(error)) } finally { setRunning(false) }
  }
  async function importReview() {
    if (!run || !feedbackFile) { toast.error("Choisissez un fichier de revue"); return }
    setFeedbackBusy(true)
    try {
      const result = await postJSON<{ reviews_imported_or_updated: number }>("/api/feedback", { run_id: run.run_id, reviews: await feedbackFile.text() })
      toast.success(`${result.reviews_imported_or_updated} décisions enregistrées. Relancez l’analyse pour voir les statuts mis à jour.`)
      setFeedbackFile(null)
    } catch (error) { toast.error(niceError(error)) } finally { setFeedbackBusy(false) }
  }
  async function importAgentEvidence() {
    if (!run || !agentArtifactFile) { toast.error("Choisissez un résultat JSON de l’agent Signaux entreprises"); return }
    setAgentBusy(true)
    try {
      const artifact = JSON.parse(await agentArtifactFile.text())
      const receipt = await postJSON<AgentReceipt>("/api/agents/evidence", { run_id: run.run_id, artifact })
      setAgentReceipt(receipt)
      toast.success(`${receipt.candidates} proposition(s) prêtes pour la revue`)
    } catch (error) { toast.error(niceError(error)) } finally { setAgentBusy(false) }
  }
  async function copyAgentMission() {
    if (!run) return
    try {
      await navigator.clipboard.writeText(`Dans le dépôt BETA Labs, lis event_machine/AGENTS.md et le fichier agent-handoff.md du run ${run.run_id} dans le répertoire de données de la machine. Délègue la recherche événement, la résolution des comptes, les signaux entreprises et le contrôle des preuves aux agents Codex. Conserve leurs propositions séparées des preuves validées; prépare les CSV d'import; Elizabeth vérifiera le workspace, les colonnes et le nombre de lignes dans Clay.`)
      toast.success("Demande pour Codex copiée")
    } catch { toast.error("Copie indisponible dans ce navigateur") }
  }
  const nav = [
    { key: "overview" as const, label: "Vue d’ensemble", icon: Sparkles, index: "01" },
    { key: "prepare" as const, label: "Nouvelle analyse", icon: FileSpreadsheet, index: "02" },
    { key: "results" as const, label: "Résultats & revue", icon: Filter, index: "03" },
    { key: "clay" as const, label: "Export Clay", icon: Link2, index: "04" },
  ]
  return <div className="app-shell">
    <aside className="sidebar" aria-label="Navigation principale">
      <a className="brand-lockup" href="#" onClick={event => { event.preventDefault(); setView("overview") }} aria-label="BETA Labs, vue d’ensemble"><img src="/brand/betalabs-original.svg" alt="BETA Labs" /></a>
      <div className="sidebar-kicker">Machine événementielle</div>
      <nav className="nav-stack" aria-label="Sections">
        {nav.map(item => <button key={item.key} type="button" className="nav-button" data-active={view === item.key} aria-current={view === item.key ? "page" : undefined} onClick={() => setView(item.key)}>
          <item.icon size={17} strokeWidth={1.8} /><span>{item.label}</span><span className="nav-index">{item.index}</span>
        </button>)}
      </nav>
      <div className="sidebar-foot"><strong>Interne · BETA Labs</strong>Les hypothèses sont identifiées. Une revue humaine reste nécessaire avant la prospection.</div>
    </aside>
    <main className="main-area">
      <div className="topbar"><span className="topbar-kicker">Intelligence pré-événement</span><span className="topbar-date">Données conservées sur cette machine <LockKeyhole className="inline-block ml-1" size={13} /></span></div>
      <div className="page-wrap">
        {view === "overview" && <>
          <div className="hero"><div><span className="eyebrow"><span className="signal-dot" /> Poste de travail BETA Labs</span><h1>Du roster au <span className="font-accent">signal.</span></h1><p>Une lecture claire de l’événement, des comptes et des personnes à prioriser pour chaque client.</p></div><Button variant="signal" size="lg" className="hero-action" onClick={() => setView("prepare")}>Nouvelle analyse <ArrowRight /></Button></div>
          {loadingLatest ? <div className="empty-state"><LoaderCircle className="animate-spin" />Chargement de la dernière analyse…</div> : !run ? <Card><div className="empty-state"><Database size={25} /><h3>Prêt pour un premier événement</h3><p>Ajoutez une liste de participants et les profils ICP des clients pour produire une sélection traçable.</p><Button onClick={() => setView("prepare")}>Préparer une analyse <ArrowRight /></Button></div></Card> : <>
            <div className="stat-grid">
              <Card className="stat-card"><div className="stat-label">Participants</div><div className="stat-value">{formatNumber(run.manifest.counts.participants)}</div><div className="stat-caption">lignes de la liste fournie</div></Card>
              <Card className="stat-card"><div className="stat-label">Entreprises</div><div className="stat-value">{formatNumber(run.manifest.counts.accounts)}</div><div className="stat-caption">comptes rapprochés</div></Card>
              <Card className="stat-card"><div className="stat-label">Évaluations ICP</div><div className="stat-value">{formatNumber(run.manifest.counts.matches)}</div><div className="stat-caption">personne × client</div></Card>
              <Card className="stat-card kpi-accent"><div className="stat-label">Pistes possibles</div><div className="stat-value">{formatNumber((run.manifest.counts.match_statuses.possible || 0) + (run.manifest.counts.match_statuses.fort || 0))}</div><div className="stat-caption">à approfondir avant contact</div></Card>
            </div>
            <div className="overview-grid">
              <Card className="workspace-card"><span className="eyebrow muted-on-dark"><span className="signal-dot" /> Dernière analyse</span><h2>{run.manifest.event_name || run.manifest.event_id.replaceAll("-", " ")}</h2><p className="muted-on-dark">{formatNumber(run.manifest.counts.match_statuses["à confirmer"])} évaluations demandent une vérification. Les seuils de CA et les signaux manquants ne sont pas supposés.</p><Button variant="signal" onClick={() => setView("results")}>Explorer les matchs <ArrowUpRight /></Button></Card>
              <Card><CardHeader className="pb-3"><CardTitle>Lecture par client</CardTitle><CardDescription>Répartition des statuts calculés</CardDescription></CardHeader><CardContent>{Object.entries(run.manifest.client_counts || {}).map(([client, counts]) => {
                const total = Object.values(counts).reduce((sum, value) => sum + value, 0) || 1
                const good = (counts.possible || 0) + (counts.fort || 0)
                return <div className="client-row" key={client}><div className="client-row-head"><strong>{client.replace(/^./, value => value.toUpperCase())}</strong><span>{good} pistes · {counts["à confirmer"] || 0} à confirmer</span></div><div className="stack-bar" aria-label={`${client}: ${good} pistes, ${counts["à confirmer"] || 0} à confirmer, ${counts.exclu || 0} exclus`}><span style={{ width: `${good / total * 100}%`, background: "#b6c94e" }} /><span style={{ width: `${(counts["à confirmer"] || 0) / total * 100}%`, background: "#d7d5cb" }} /><span style={{ width: `${(counts.exclu || 0) / total * 100}%`, background: "#a3a29c" }} /></div></div>
              })}</CardContent></Card>
            </div>
            <div className="mt-8"><SectionHeading title="Prochaine décision" subtitle="Passez des comptes à vérifier aux conversations utiles." /></div>
            <div className="steps-grid">
              <Card className="step-card"><span className="step-no">1</span><h3>Examiner les priorités</h3><p>Filtrer les personnes par client, statut et score. Chaque ligne garde sa raison et sa source.</p></Card>
              <Card className="step-card"><span className="step-no">2</span><h3>Corriger les hypothèses</h3><p>Importer une revue humaine pour améliorer le rang des analyses futures.</p></Card>
              <Card className="step-card"><span className="step-no">3</span><h3>Exporter vers Clay</h3><p>Télécharger le CSV prioritaire, vérifier les lignes et l’importer dans le workspace choisi par Elizabeth.</p></Card>
            </div>
          </>}
        </>}

        {view === "prepare" && <>
          <div className="hero"><div><span className="eyebrow"><span className="signal-dot" /> Nouvelle analyse</span><h1>Préparer une <span className="font-accent">sélection.</span></h1><p>Deux entrées suffisent : une liste de participants et les ICP des clients. Les comptes et relations sont optionnels.</p></div><Button variant="outline" onClick={loadHopExample}>Charger l’exemple HOP</Button></div>
          <div className="grid gap-5 max-w-[1050px]">
            <Card><CardHeader><div className="flex items-center gap-3"><span className="step-no">1</span><div><CardTitle>Définir l’événement</CardTitle><CardDescription>Édition précise, source officielle et marqueur d’inscription si disponible.</CardDescription></div></div></CardHeader><CardContent className="form-grid">
              <div className="form-stack"><div><Label htmlFor="event-name">Nom de l’événement *</Label><Input id="event-name" className="mt-2" placeholder="Ex. HOP! Le Sommet du commerce de détail 2026" value={eventForm.name} onChange={event => setEventForm({ ...eventForm, name: event.target.value })} /></div><div><Label htmlFor="event-id">Identifiant de l’édition *</Label><Input id="event-id" className="mt-2 mono" placeholder="ex. hop-2026" value={eventForm.id} onChange={event => setEventForm({ ...eventForm, id: event.target.value })} /></div><div><Label htmlFor="event-url">URL officielle</Label><Input id="event-url" type="url" className="mt-2" placeholder="https://…" value={eventForm.url} onChange={event => setEventForm({ ...eventForm, url: event.target.value })} /></div></div>
              <div className="form-stack"><div><Label htmlFor="event-date">Date</Label><Input id="event-date" type="date" className="mt-2" value={eventForm.date} onChange={event => setEventForm({ ...eventForm, date: event.target.value })} /></div><div><Label htmlFor="event-edition">Édition</Label><Input id="event-edition" className="mt-2" placeholder="2026" value={eventForm.edition} onChange={event => setEventForm({ ...eventForm, edition: event.target.value })} /></div><div><Label htmlFor="event-marker">Marqueur d’inscription</Label><Input id="event-marker" className="mt-2 mono" placeholder="ex. pairconnex-test-a" value={eventForm.registration_marker} onChange={event => setEventForm({ ...eventForm, registration_marker: event.target.value })} /><p className="field-note mt-2">Sans ce marqueur, la présence reste fondée sur la liste fournie.</p></div></div>
              <label className="check-row col-span-full mt-2"><input type="checkbox" checked={offline} onChange={event => setOffline(event.target.checked)} /><span><strong>Utiliser les pages fournies, sans recherche réseau</strong><br /><span className="field-note">Utile pour rejouer une analyse ou si l’accès aux sites est bloqué.</span></span></label>
            </CardContent></Card>
            <Card><CardHeader><div className="flex items-center gap-3"><span className="step-no">2</span><div><CardTitle>Importer les données</CardTitle><CardDescription>Conservez les CSV d’origine ; la machine produit ses propres exports.</CardDescription></div></div></CardHeader><CardContent><div className="file-grid">{FILES.map(file => <FileDrop key={file.key} title={file.title} note={file.note} required={file.required} value={uploads[file.key]} onChange={value => setUpload(file.key, value)} />)}</div><p className="field-note mt-4 flex gap-2"><ShieldCheck size={15} className="shrink-0 mt-0.5" /> L’import reste sur cette machine. Un CA estimé ou sans source ne valide pas un seuil ICP.</p></CardContent></Card>
            <Card><CardHeader><div className="flex items-center gap-3"><span className="step-no">3</span><div><CardTitle>Ajouter les profils ICP</CardTitle><CardDescription>Un résultat sera calculé pour chaque participant et chaque client.</CardDescription></div></div></CardHeader><CardContent><div className="flex flex-wrap items-center gap-3 mb-4"><label className="relative"><Input type="file" accept=".json,application/json" className="absolute h-1 w-1 opacity-0" aria-label="Importer les profils ICP JSON" onChange={event => importIcp(event.target.files?.[0] || null)} /><span className="inline-flex h-10 items-center gap-2 rounded-md border border-[#c9c9c3] bg-white px-4 text-sm font-semibold cursor-pointer"><Upload size={16} /> Importer un JSON</span></label><span className="field-note">ou coller la configuration ci-dessous</span></div>
              {icpNames.length > 0 && <div className="flex flex-wrap gap-2 mb-4">{icpNames.map((name, index) => <Badge variant="signal" key={`${name}-${index}`}>{name}</Badge>)}</div>}
              <Label htmlFor="icp-json">Configuration ICP (JSON) *</Label><Textarea id="icp-json" className="mt-2 mono min-h-44 text-xs" placeholder={'{"clients":[{"id":"client","target":{"company_types":["retailer"]}}]}'} value={icpJson} onChange={event => setIcpJson(event.target.value)} />
              {icpJson && !icpNames.length && <p className="field-error">Le JSON doit être valide et contenir un tableau « clients ».</p>}
              <p className="field-note mt-2">Les règles de rôle, secteur, revenus et signaux restent explicites dans ce fichier.</p>
              <hr className="soft-rule" /><div className="flex flex-wrap items-center justify-between gap-3"><div><strong className="text-sm">Prêt à analyser ?</strong><p className="field-note mt-1">{uploads.participants ? uploads.participants.name : "Liste des participants manquante"} · {icpNames.length} profil{icpNames.length > 1 ? "s" : ""} ICP</p></div><Button variant="signal" size="lg" disabled={running} onClick={runAnalysis}>{running ? <><LoaderCircle className="animate-spin" /> Analyse en cours…</> : <>Lancer l’analyse <ArrowRight /></>}</Button></div>
            </CardContent></Card>
          </div>
        </>}

        {view === "results" && <>
          <div className="hero"><div><span className="eyebrow"><span className="signal-dot" /> Résultats & revue</span><h1>Comprendre chaque <span className="font-accent">match.</span></h1><p>Le statut, les preuves et les questions ouvertes restent visibles avant toute activation commerciale.</p></div>{run && <Button variant="outline" onClick={() => setView("prepare")}>Nouvelle analyse <ArrowRight /></Button>}</div>
          {!run ? <Card><div className="empty-state"><Search size={27} /><h3>Aucune analyse à consulter</h3><p>Commencez par importer une liste et les profils ICP des clients.</p><Button onClick={() => setView("prepare")}>Préparer une analyse</Button></div></Card> : <>
            <div className="stat-grid"><Card className="stat-card"><div className="stat-label">Évaluations</div><div className="stat-value">{formatNumber(run.manifest.counts.matches)}</div></Card><Card className="stat-card kpi-accent"><div className="stat-label">Fort / possible</div><div className="stat-value">{formatNumber((run.manifest.counts.match_statuses.fort || 0) + (run.manifest.counts.match_statuses.possible || 0))}</div></Card><Card className="stat-card"><div className="stat-label">À confirmer</div><div className="stat-value">{formatNumber(run.manifest.counts.match_statuses["à confirmer"])}</div></Card><Card className="stat-card"><div className="stat-label">Exclus</div><div className="stat-value">{formatNumber(run.manifest.counts.match_statuses.exclu)}</div></Card></div>
            <Tabs defaultValue="matches"><TabsList className="mb-4 h-auto flex-wrap justify-start"><TabsTrigger value="matches">Matchs & priorités</TabsTrigger><TabsTrigger value="context">Contexte événement</TabsTrigger><TabsTrigger value="agents">Agents & preuves</TabsTrigger><TabsTrigger value="exports">Exports & corrections</TabsTrigger></TabsList>
              <TabsContent value="matches"><Card><CardHeader><div className="result-toolbar"><div><CardTitle>Liste de qualification</CardTitle><CardDescription className="mt-1">{loadingOutputs ? "Lecture des résultats…" : `${formatNumber(filtered.length)} lignes affichables. Ouvrez une ligne pour voir les raisons.`}</CardDescription></div><div className="filter-row"><div className="relative"><Search className="absolute left-3 top-3 text-[#8a8a84]" size={15} /><Input className="pl-9 w-[235px]" aria-label="Rechercher personne ou entreprise" placeholder="Personne ou entreprise" value={search} onChange={event => setSearch(event.target.value)} /></div><Select value={clientFilter} onValueChange={setClientFilter}><SelectTrigger className="w-[165px]" aria-label="Filtrer par client"><SelectValue placeholder="Tous les clients" /></SelectTrigger><SelectContent><SelectItem value="all">Tous les clients</SelectItem>{clientOptions.map(([id, name]) => <SelectItem key={id} value={id}>{name}</SelectItem>)}</SelectContent></Select><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="w-[155px]" aria-label="Filtrer par statut"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="priority">À traiter</SelectItem><SelectItem value="all">Tous</SelectItem><SelectItem value="fort">Fort</SelectItem><SelectItem value="possible">Possible</SelectItem><SelectItem value="à confirmer">À confirmer</SelectItem><SelectItem value="exclu">Exclu</SelectItem></SelectContent></Select></div></div></CardHeader>
                <CardContent className="px-0 pb-0">{loadingOutputs ? <div className="empty-state"><LoaderCircle className="animate-spin" />Chargement…</div> : !visible.length ? <div className="empty-state"><CircleHelp size={24} /><h3>Aucune ligne pour ce filtre</h3><p>Essayez un autre client, statut ou terme de recherche.</p></div> : <Table><TableHeader><TableRow><TableHead>Participant</TableHead><TableHead>Entreprise</TableHead><TableHead>Client</TableHead><TableHead>Statut</TableHead><TableHead className="text-right">Priorité</TableHead><TableHead className="w-10"><span className="sr-only">Détail</span></TableHead></TableRow></TableHeader><TableBody>{visible.map(row => <TableRow key={row.match_key} className="cursor-pointer" onClick={() => setSelected(row)}><TableCell><button type="button" className="text-left font-semibold hover:underline">{row.person_name || "À confirmer"}</button><div className="text-xs text-[#888880] mt-1 max-w-[200px] truncate">{row.job_title || "Poste à confirmer"}</div></TableCell><TableCell className="max-w-[180px] truncate">{row.company_name}</TableCell><TableCell>{row.client_name}</TableCell><TableCell>{fitBadge(row.fit_status)}</TableCell><TableCell className="text-right font-semibold tabular-nums">{row.priority_score}</TableCell><TableCell><ChevronRight size={16} className="text-[#9b9b93]" /></TableCell></TableRow>)}</TableBody></Table>}
                  {filtered.length > 25 && <div className="flex items-center justify-between gap-3 border-t border-[#e8e6df] px-6 py-4"><span className="field-note">{page * 25 + 1}–{Math.min((page + 1) * 25, filtered.length)} sur {formatNumber(filtered.length)}</span><div className="flex gap-2"><Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}><ArrowLeft /> Précédent</Button><Button variant="outline" size="sm" disabled={(page + 1) * 25 >= filtered.length} onClick={() => setPage(page + 1)}>Suivant <ArrowRight /></Button></div></div>}
                </CardContent></Card><p className="field-note mt-3">La priorité aide à trier; elle ne remplace pas une preuve de chiffre d’affaires, de projet ou d’intention.</p></TabsContent>
              <TabsContent value="context"><Card><CardHeader><CardTitle>Cartographie de l’événement</CardTitle><CardDescription>{run.manifest.counts.event_pages} page(s) lue(s) · {run.manifest.counts.research_errors} erreur(s) de recherche</CardDescription></CardHeader><CardContent><Suspense fallback={<div className="text-sm text-[#777770]">Chargement du contexte…</div>}><EventMarkdown content={brief} /></Suspense><Button variant="outline" className="mt-5" asChild><a href={download(run.run_id, "event-brief.md")} download>Exporter le rapport <ArrowDownToLine /></a></Button></CardContent></Card></TabsContent>
              <TabsContent value="agents"><div className="grid gap-5 lg:grid-cols-2"><Card><CardHeader><CardTitle>Mission des agents</CardTitle><CardDescription>Des spécialistes Codex travaillent sur les sources; le moteur garde la décision ICP.</CardDescription></CardHeader><CardContent><div className="grid gap-3 text-sm text-[#5f5f59]"><p><strong>1. Recherche événement</strong> · Contexte, acheteurs et vendeurs avec sources.</p><p><strong>2. Résolution des comptes</strong> · Rattachements et conflits à vérifier.</p><p><strong>3. Signaux entreprises</strong> · Faits ciblés sur les critères des clients.</p><p><strong>4. Contrôle des preuves</strong> · Citation, date et incertitude.</p></div><div className="mt-5 flex flex-wrap gap-2"><Button variant="signal" disabled={!run.files.includes("agent-handoff.md")} onClick={copyAgentMission}>Copier la demande Codex <ArrowRight /></Button>{run.files.includes("agent-handoff.md") ? <Button variant="outline" asChild><a href={download(run.run_id, "agent-handoff.md")} download>Télécharger la mission <ArrowDownToLine /></a></Button> : <p className="field-note">Cette analyse précède le flux d’agents. Relancez-la pour obtenir une mission dédiée.</p>}</div><p className="field-note mt-3">Ces rôles sont lancés dans la tâche Codex cloud. La recherche live dépend des domaines autorisés par cet environnement.</p></CardContent></Card><Card><CardHeader><CardTitle>Importer des signaux proposés</CardTitle><CardDescription>Le JSON de l’agent devient un CSV de candidats séparé des preuves validées.</CardDescription></CardHeader><CardContent><Label htmlFor="agent-evidence-upload">Résultat JSON de l’agent Signaux entreprises</Label><Input id="agent-evidence-upload" type="file" accept=".json,application/json" className="mt-2" onChange={event => setAgentArtifactFile(event.target.files?.[0] || null)} /><Button className="mt-4" disabled={!agentArtifactFile || agentBusy} onClick={importAgentEvidence}>{agentBusy ? <LoaderCircle className="animate-spin" /> : <Check />} Vérifier le format</Button>{agentReceipt && <div className="rounded-lg border border-[#d7dcad] bg-[#f7fae9] p-4 mt-5 text-sm"><strong>{agentReceipt.candidates} signal(s) à revoir</strong><p className="mt-1 mb-3 text-[#696961]">La confiance reste faible. Vérifiez chaque page et citation avant de réimporter le CSV comme preuve.</p><Button variant="outline" asChild><a href={agentReceipt.candidate_url} download>Télécharger les candidats <ArrowDownToLine /></a></Button></div>}<p className="field-note mt-4">Une proposition d’agent ne valide jamais seule un CA, un signal ICP ou une inscription.</p></CardContent></Card></div></TabsContent>
              <TabsContent value="exports"><div className="grid gap-5 lg:grid-cols-2"><Card><CardHeader><CardTitle>Livrables</CardTitle><CardDescription>Fichiers de cette analyse, avec clés et provenance.</CardDescription></CardHeader><CardContent><div className="download-grid">{run.files.map(file => <a className="download-link" key={file} href={download(run.run_id, file)} download><span>{OUTPUT_NAMES[file] || file}<small className="block text-[#8a8a84] font-normal mt-1 mono">{file}</small></span><ArrowDownToLine size={15} /></a>)}</div></CardContent></Card><Card><CardHeader><CardTitle>Apprentissage par revue</CardTitle><CardDescription>Les décisions humaines restent distinctes du calcul machine.</CardDescription></CardHeader><CardContent><p className="text-sm leading-6 text-[#676761] mb-5">Téléchargez le modèle, renseignez le statut retenu, le réviseur et la preuve, puis importez le fichier complété. Une nouvelle analyse appliquera les corrections.</p><Button variant="outline" asChild><a href={download(run.run_id, "feedback-template.csv")} download>1. Télécharger le modèle <ArrowDownToLine /></a></Button><div className="mt-6"><Label htmlFor="feedback-upload">2. Importer la revue complétée</Label><Input id="feedback-upload" type="file" accept=".csv,text/csv" className="mt-2" onChange={event => setFeedbackFile(event.target.files?.[0] || null)} /></div><Button className="mt-4" disabled={!feedbackFile || feedbackBusy} onClick={importReview}>{feedbackBusy ? <LoaderCircle className="animate-spin" /> : <Check />} Enregistrer les décisions</Button><p className="field-note mt-3">Une décision « fort » exige une URL de preuve. Le retour ajuste le classement futur sans changer les exclusions.</p></CardContent></Card></div></TabsContent>
            </Tabs>
          </>}
        </>}

        {view === "clay" && <>
          <div className="hero"><div><span className="eyebrow"><span className="signal-dot" /> Export vers Clay</span><h1>Livrer sans <span className="font-accent">webhook.</span></h1><p>Téléchargez un CSV prêt pour Clay, puis importez-le dans le workspace choisi par Elizabeth. Aucun endpoint ni abonnement webhook requis pour ce parcours.</p></div>{run && <Badge variant="signal">Analyse {run.manifest.event_id} prête</Badge>}</div>
          {!run ? <Card><div className="empty-state"><Database size={25} /><h3>Aucune analyse à exporter</h3><p>Lancez d’abord une analyse pour créer les fichiers Clay.</p><Button onClick={() => setView("prepare")}>Préparer une analyse <ArrowRight /></Button></div></Card> : <div className="grid gap-5 max-w-[1050px]">
            <Card className="border-[#d7dcad]"><CardHeader><CardTitle>1. Choisir le lot à importer</CardTitle><CardDescription>Une ligne par participant et par client, avec une clé stable et les raisons du match.</CardDescription></CardHeader><CardContent><div className="grid gap-3 sm:grid-cols-2"><div className="rounded-xl border border-[#d7dcad] bg-[#f8fbea] p-5"><Badge variant="signal">{formatNumber((run.manifest.counts.match_statuses.fort || 0) + (run.manifest.counts.match_statuses.possible || 0))} pistes</Badge><h3 className="mt-3 mb-1 text-base font-semibold">Liste prioritaire</h3><p className="mb-4 text-xs leading-5 text-[#686861]">Statuts fort et possible. Bon point de départ pour la prospection après vérification des preuves.</p>{run.files.includes("clay-import-priority.csv") ? <Button variant="signal" asChild><a href={download(run.run_id, "clay-import-priority.csv")} download>Télécharger le CSV <ArrowDownToLine /></a></Button> : <span className="field-note">Relancez l’analyse pour créer ce fichier.</span>}</div><div className="rounded-xl border border-[#e5e3dd] bg-white p-5"><Badge variant="outline">{formatNumber(run.manifest.counts.matches)} évaluations</Badge><h3 className="mt-3 mb-1 text-base font-semibold">Tous les matchs</h3><p className="mb-4 text-xs leading-5 text-[#686861]">Inclut les cas à confirmer et exclus, pour une table de suivi complète.</p><Button variant="outline" asChild><a href={download(run.run_id, run.files.includes("clay-import-all.csv") ? "clay-import-all.csv" : "matches.csv")} download>Télécharger le CSV <ArrowDownToLine /></a></Button></div></div><p className="field-note mt-4">Les colonnes comprennent <code className="mono">match_key</code>, l’événement, le client, la personne, l’entreprise, le statut, la priorité et les sources.</p></CardContent></Card>
            <Card><CardHeader><CardTitle>2. Importer dans Clay</CardTitle><CardDescription>Elizabeth utilise son compte Clay directement; cette application n’a pas besoin de son jeton.</CardDescription></CardHeader><CardContent><ol className="list-decimal pl-5 space-y-3 text-sm leading-6 text-[#62625c]"><li>Ouvrir le bon workspace dans <a href="https://app.clay.com" target="_blank" rel="noreferrer" className="underline font-semibold">Clay <ArrowUpRight className="inline-block" size={13} /></a> et choisir l’import d’un fichier CSV.</li><li>Déposer le fichier téléchargé et vérifier l’aperçu des colonnes ainsi que le nombre de lignes avant de confirmer l’import.</li><li>Conserver <code className="mono">match_key</code> comme identifiant de rapprochement pour repérer les doublons lors d’un prochain import.</li></ol><p className="field-note mt-5">L’import est effectué dans Clay par Elizabeth. La machine ne peut pas confirmer à elle seule que les lignes ont été ajoutées.</p></CardContent></Card>
            <Card><CardHeader><CardTitle>Autres données disponibles</CardTitle><CardDescription>Importer séparément si l’équipe veut des tables de référence.</CardDescription></CardHeader><CardContent><div className="download-grid">{[["participants.csv", "Participants"], ["accounts.csv", "Entreprises"], ["evidence.csv", "Preuves et signaux"]].map(([file, label]) => <a className="download-link" key={file} href={download(run.run_id, file)} download><span>{label}<small className="block text-[#8a8a84] font-normal mt-1 mono">{file}</small></span><ArrowDownToLine size={15} /></a>)}</div></CardContent></Card>
          </div>}
        </>}

      </div>
    </main>
    <Dialog open={!!selected} onOpenChange={open => { if (!open) setSelected(null) }}><DialogContent><DialogHeader><DialogTitle>{selected?.person_name || "Participant"}</DialogTitle><DialogDescription>{selected?.job_title || "Poste à confirmer"} · {selected?.company_name || "Entreprise à confirmer"}</DialogDescription></DialogHeader>{selected && <div className="grid gap-4"><div className="flex flex-wrap items-center gap-2">{fitBadge(selected.fit_status)}<Badge variant="muted">{selected.client_name}</Badge><span className="text-xs text-[#72726c] ml-auto">Priorité {selected.priority_score}/100</span></div><div className="detail-grid"><div className="detail-block"><dt>Pourquoi participer ?</dt><dd>{selected.why_attend || "À confirmer"}</dd></div><div className="detail-block"><dt>Objectif d’affaires</dt><dd>{selected.business_objective || "À confirmer"}</dd></div><div className="detail-block"><dt>Raison du match</dt><dd>{splitPipe(selected.fit_reasons).length ? splitPipe(selected.fit_reasons).join(" · ") : "Aucune réserve documentée"}</dd></div><div className="detail-block"><dt>Angle pour {selected.client_name}</dt><dd>{selected.opportunity_hypothesis}</dd></div></div>{selected.exclusion_reasons && <div className="rounded-lg bg-[#f7ece9] p-4 text-sm"><strong>Exclusions :</strong> {splitPipe(selected.exclusion_reasons).join(" · ")}</div>}<div className="rounded-lg bg-white border border-[#e5e3dd] p-4"><div className="text-xs uppercase tracking-wider font-bold text-[#777770] mb-2">Question de découverte</div><p className="text-sm leading-6 m-0">{selected.next_question}</p></div><div className="text-xs text-[#777770]"><strong>Sources :</strong> {splitPipe(selected.evidence_urls).length ? splitPipe(selected.evidence_urls).filter(url => /^https?:\/\//.test(url)).map(url => <a key={url} href={url} target="_blank" rel="noreferrer" className="block underline break-all mt-1">{url}</a>) : "Aucune preuve externe liée à cette ligne."}</div></div>}</DialogContent></Dialog>
  </div>
}

export default App
