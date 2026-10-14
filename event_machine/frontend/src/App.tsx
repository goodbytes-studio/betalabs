import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react"
import Papa from "papaparse"
import { toast } from "sonner"
import {
  ArrowDownToLine, ArrowLeft, ArrowRight, ArrowUpRight, Check, CheckCircle2, ChevronRight,
  CircleHelp, CloudUpload, Database, FileCheck2, FileSpreadsheet,
  Filter, Link2, LoaderCircle, LockKeyhole, LogIn, Search, ShieldCheck, Sparkles, Upload,
  XCircle,
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
type Workspace = { id: string; name?: string; active?: boolean }
type ClayStatus = { active: { user_id?: string; user_email?: string; workspace_id?: string; workspace_name?: string; signed_in_workspaces?: Workspace[]; error?: string }; pinned: { user_id?: string; user_email?: string; workspace_id?: string; workspace_name?: string }; configured_tables: string[]; login_state: string; verification_url?: string; user_code?: string; login_error?: string }
type ClayPreview = { runId: string; table: string; pending: number; already_sent: number; source_rows: number; destination_fingerprint: string }
type EventForm = { id: string; name: string; edition: string; date: string; url: string; registration_marker: string }
type InputKey = "participants" | "accounts" | "relations" | "evidence"

const EMPTY_EVENT: EventForm = { id: "", name: "", edition: "", date: "", url: "", registration_marker: "" }
const OUTPUT_NAMES: Record<string, string> = {
  "matches.csv": "Matchs ICP", "review-queue.csv": "File de revue", "participants.csv": "Participants qualifiés",
  "accounts.csv": "Entreprises rapprochées", "event-brief.md": "Contexte de l’événement",
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
  const [clay, setClay] = useState<ClayStatus | null>(null)
  const [clayBusy, setClayBusy] = useState(false)
  const [workspaceChoice, setWorkspaceChoice] = useState("")
  const [clayTable, setClayTable] = useState("matches")
  const [webhook, setWebhook] = useState("")
  const [clayPreview, setClayPreview] = useState<ClayPreview | null>(null)
  const [clayMessage, setClayMessage] = useState("")

  const refreshClay = useCallback(async () => {
    try {
      const status = await getJSON<ClayStatus>("/api/clay/status")
      setClay(status)
      setWorkspaceChoice(previous => previous || status.active.workspace_id || "")
    } catch (error) { toast.error(niceError(error)) }
  }, [])

  useEffect(() => {
    getJSON<Run>("/api/runs/latest").then(setRun).catch(() => {}).finally(() => setLoadingLatest(false))
    refreshClay()
  }, [refreshClay])
  useEffect(() => {
    if (clay?.login_state !== "running") return
    const timer = window.setInterval(refreshClay, 3500)
    return () => window.clearInterval(timer)
  }, [clay?.login_state, refreshClay])
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
      setClayPreview(null)
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
  async function clayAction(action: string, details: Record<string, unknown> = {}) {
    setClayBusy(true)
    try {
      const result = await postJSON<Record<string, unknown>>("/api/clay", { action, ...details })
      if (action === "login") toast.info("Le code de connexion Clay va s’afficher ci-dessous")
      if (action === "switch") { setWorkspaceChoice(String((result.workspace as Workspace)?.id || "")); toast.success("Workspace actif mis à jour") }
      if (action === "pin") toast.success("Compte et workspace confirmés")
      if (action === "webhook") { setWebhook(""); setClayPreview(null); toast.success("Destination Clay enregistrée") }
      if (action === "push") {
        if (details.apply) { setClayPreview(null); toast.success(`${result.sent || 0} lignes envoyées vers Clay`); setClayMessage(`Envoi terminé · ${result.sent || 0} lignes transmises.`) }
        else {
          setClayPreview({ runId: run!.run_id, table: clayTable, pending: Number(result.pending || 0), already_sent: Number(result.already_sent || 0), source_rows: Number(result.source_rows || 0), destination_fingerprint: String(result.destination_fingerprint || "") })
          setClayMessage("Prévisualisation prête. Vérifiez le nombre de lignes et la destination avant l’envoi.")
        }
      }
      await refreshClay()
    } catch (error) { toast.error(niceError(error)) } finally { setClayBusy(false) }
  }

  const nav = [
    { key: "overview" as const, label: "Vue d’ensemble", icon: Sparkles, index: "01" },
    { key: "prepare" as const, label: "Nouvelle analyse", icon: FileSpreadsheet, index: "02" },
    { key: "results" as const, label: "Résultats & revue", icon: Filter, index: "03" },
    { key: "clay" as const, label: "Connexion Clay", icon: Link2, index: "04" },
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
              <Card className="step-card"><span className="step-no">3</span><h3>Préparer Clay</h3><p>Vérifier l’identité d’Elizabeth, la table cible et les lignes en attente avant l’envoi.</p></Card>
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
            <Tabs defaultValue="matches"><TabsList className="mb-4"><TabsTrigger value="matches">Matchs & priorités</TabsTrigger><TabsTrigger value="context">Contexte événement</TabsTrigger><TabsTrigger value="exports">Exports & corrections</TabsTrigger></TabsList>
              <TabsContent value="matches"><Card><CardHeader><div className="result-toolbar"><div><CardTitle>Liste de qualification</CardTitle><CardDescription className="mt-1">{loadingOutputs ? "Lecture des résultats…" : `${formatNumber(filtered.length)} lignes affichables. Ouvrez une ligne pour voir les raisons.`}</CardDescription></div><div className="filter-row"><div className="relative"><Search className="absolute left-3 top-3 text-[#8a8a84]" size={15} /><Input className="pl-9 w-[235px]" aria-label="Rechercher personne ou entreprise" placeholder="Personne ou entreprise" value={search} onChange={event => setSearch(event.target.value)} /></div><Select value={clientFilter} onValueChange={setClientFilter}><SelectTrigger className="w-[165px]" aria-label="Filtrer par client"><SelectValue placeholder="Tous les clients" /></SelectTrigger><SelectContent><SelectItem value="all">Tous les clients</SelectItem>{clientOptions.map(([id, name]) => <SelectItem key={id} value={id}>{name}</SelectItem>)}</SelectContent></Select><Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="w-[155px]" aria-label="Filtrer par statut"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="priority">À traiter</SelectItem><SelectItem value="all">Tous</SelectItem><SelectItem value="fort">Fort</SelectItem><SelectItem value="possible">Possible</SelectItem><SelectItem value="à confirmer">À confirmer</SelectItem><SelectItem value="exclu">Exclu</SelectItem></SelectContent></Select></div></div></CardHeader>
                <CardContent className="px-0 pb-0">{loadingOutputs ? <div className="empty-state"><LoaderCircle className="animate-spin" />Chargement…</div> : !visible.length ? <div className="empty-state"><CircleHelp size={24} /><h3>Aucune ligne pour ce filtre</h3><p>Essayez un autre client, statut ou terme de recherche.</p></div> : <Table><TableHeader><TableRow><TableHead>Participant</TableHead><TableHead>Entreprise</TableHead><TableHead>Client</TableHead><TableHead>Statut</TableHead><TableHead className="text-right">Priorité</TableHead><TableHead className="w-10"><span className="sr-only">Détail</span></TableHead></TableRow></TableHeader><TableBody>{visible.map(row => <TableRow key={row.match_key} className="cursor-pointer" onClick={() => setSelected(row)}><TableCell><button type="button" className="text-left font-semibold hover:underline">{row.person_name || "À confirmer"}</button><div className="text-xs text-[#888880] mt-1 max-w-[200px] truncate">{row.job_title || "Poste à confirmer"}</div></TableCell><TableCell className="max-w-[180px] truncate">{row.company_name}</TableCell><TableCell>{row.client_name}</TableCell><TableCell>{fitBadge(row.fit_status)}</TableCell><TableCell className="text-right font-semibold tabular-nums">{row.priority_score}</TableCell><TableCell><ChevronRight size={16} className="text-[#9b9b93]" /></TableCell></TableRow>)}</TableBody></Table>}
                  {filtered.length > 25 && <div className="flex items-center justify-between gap-3 border-t border-[#e8e6df] px-6 py-4"><span className="field-note">{page * 25 + 1}–{Math.min((page + 1) * 25, filtered.length)} sur {formatNumber(filtered.length)}</span><div className="flex gap-2"><Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}><ArrowLeft /> Précédent</Button><Button variant="outline" size="sm" disabled={(page + 1) * 25 >= filtered.length} onClick={() => setPage(page + 1)}>Suivant <ArrowRight /></Button></div></div>}
                </CardContent></Card><p className="field-note mt-3">La priorité aide à trier; elle ne remplace pas une preuve de chiffre d’affaires, de projet ou d’intention.</p></TabsContent>
              <TabsContent value="context"><Card><CardHeader><CardTitle>Cartographie de l’événement</CardTitle><CardDescription>{run.manifest.counts.event_pages} page(s) lue(s) · {run.manifest.counts.research_errors} erreur(s) de recherche</CardDescription></CardHeader><CardContent><Suspense fallback={<div className="text-sm text-[#777770]">Chargement du contexte…</div>}><EventMarkdown content={brief} /></Suspense><Button variant="outline" className="mt-5" asChild><a href={download(run.run_id, "event-brief.md")} download>Exporter le rapport <ArrowDownToLine /></a></Button></CardContent></Card></TabsContent>
              <TabsContent value="exports"><div className="grid gap-5 lg:grid-cols-2"><Card><CardHeader><CardTitle>Livrables</CardTitle><CardDescription>Fichiers de cette analyse, avec clés et provenance.</CardDescription></CardHeader><CardContent><div className="download-grid">{run.files.map(file => <a className="download-link" key={file} href={download(run.run_id, file)} download><span>{OUTPUT_NAMES[file] || file}<small className="block text-[#8a8a84] font-normal mt-1 mono">{file}</small></span><ArrowDownToLine size={15} /></a>)}</div></CardContent></Card><Card><CardHeader><CardTitle>Apprentissage par revue</CardTitle><CardDescription>Les décisions humaines restent distinctes du calcul machine.</CardDescription></CardHeader><CardContent><p className="text-sm leading-6 text-[#676761] mb-5">Téléchargez le modèle, renseignez le statut retenu, le réviseur et la preuve, puis importez le fichier complété. Une nouvelle analyse appliquera les corrections.</p><Button variant="outline" asChild><a href={download(run.run_id, "feedback-template.csv")} download>1. Télécharger le modèle <ArrowDownToLine /></a></Button><div className="mt-6"><Label htmlFor="feedback-upload">2. Importer la revue complétée</Label><Input id="feedback-upload" type="file" accept=".csv,text/csv" className="mt-2" onChange={event => setFeedbackFile(event.target.files?.[0] || null)} /></div><Button className="mt-4" disabled={!feedbackFile || feedbackBusy} onClick={importReview}>{feedbackBusy ? <LoaderCircle className="animate-spin" /> : <Check />} Enregistrer les décisions</Button><p className="field-note mt-3">Une décision « fort » exige une URL de preuve. Le retour ajuste le classement futur sans changer les exclusions.</p></CardContent></Card></div></TabsContent>
            </Tabs>
          </>}
        </>}

        {view === "clay" && <>
          <div className="hero"><div><span className="eyebrow"><span className="signal-dot" /> Connexion Clay</span><h1>Livrer avec <span className="font-accent">contrôle.</span></h1><p>Elizabeth autorise son compte. La machine vérifie l’identité, le workspace et la destination avant chaque envoi.</p></div>{run && <Badge variant="signal">Analyse {run.manifest.event_id} prête</Badge>}</div>
          <div className="grid gap-5 max-w-[1050px]">
            <Card><CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><div><CardTitle>État de la connexion</CardTitle><CardDescription className="mt-1">L’accès au dépôt Git ne connecte pas automatiquement Clay.</CardDescription></div>{clay?.active.user_id ? <Badge variant="signal"><CheckCircle2 size={12} className="mr-1" /> Authentifié</Badge> : <Badge variant="outline"><XCircle size={12} className="mr-1" /> Non connecté</Badge>}</div></CardHeader><CardContent><div className="grid gap-3 sm:grid-cols-2"><div className="detail-block"><dt>Compte actif</dt><dd>{clay?.active.user_email || (clay?.active.error ? "Aucune session Clay active" : "Vérification en cours")}</dd></div><div className="detail-block"><dt>Workspace actif</dt><dd>{clay?.active.workspace_name || clay?.active.workspace_id || "À connecter"}</dd></div></div>{clay?.pinned.user_id && <div className="mt-3 flex items-center gap-2 text-xs text-[#64645c]"><ShieldCheck size={15} /> Compte épinglé : {clay.pinned.user_email || clay.pinned.user_id} · {clay.pinned.workspace_name || clay.pinned.workspace_id}</div>}</CardContent></Card>
            <div className="clay-steps">
              <div className="clay-step"><span className="step-no">1</span><div><h3>Autoriser le compte Clay</h3><p>Obtenez un code de connexion, ouvrez le lien Clay et autorisez l’accès avec le compte d’Elizabeth.</p><div className="flex flex-wrap gap-2 mt-4"><Button disabled={clayBusy || clay?.login_state === "running"} onClick={() => clayAction("login")}>{clay?.login_state === "running" ? <LoaderCircle className="animate-spin" /> : <LogIn />} {clay?.login_state === "running" ? "Connexion en cours…" : "Obtenir un code Clay"}</Button><Button variant="outline" disabled={clayBusy} onClick={refreshClay}>Vérifier la connexion</Button></div>{clay?.verification_url && <div className="mt-4 rounded-lg border border-[#d4de91] bg-[#fbfde9] p-4 text-sm"><a className="font-semibold underline break-all" href={clay.verification_url} target="_blank" rel="noreferrer">Ouvrir la page d’autorisation Clay <ArrowUpRight className="inline-block ml-1" size={14} /></a>{clay.user_code && <p className="mt-3 mb-0">Code : <strong className="mono text-lg tracking-widest">{clay.user_code}</strong></p>}</div>}{clay?.login_state === "failed" && <p className="field-error mt-3">La connexion a échoué{clay.login_error ? ` : ${clay.login_error}` : " dans cet environnement"}. Lancez <code className="mono">clay login</code> sur l’ordinateur qui héberge la machine, puis revérifiez.</p>}<p className="field-note mt-3">Les autorisations et jetons sont gérés par le CLI Clay, jamais par cette page.</p></div></div>
              <div className="clay-step"><span className="step-no">2</span><div><h3>Choisir et confirmer le workspace</h3><p>Vérifiez le compte affiché, puis fixez le workspace utilisé pour tous les envois.</p><div className="flex flex-wrap items-center gap-2 mt-4"><Select value={workspaceChoice || undefined} onValueChange={setWorkspaceChoice}><SelectTrigger className="w-full max-w-[280px]" aria-label="Choisir le workspace Clay"><SelectValue placeholder="Choisir un workspace" /></SelectTrigger><SelectContent>{(clay?.active.signed_in_workspaces?.length ? clay.active.signed_in_workspaces : clay?.active.workspace_id ? [{ id: clay.active.workspace_id, name: clay.active.workspace_name, active: true }] : []).map(workspace => <SelectItem key={workspace.id} value={String(workspace.id)}>{workspace.name || workspace.id}</SelectItem>)}</SelectContent></Select><Button variant="outline" disabled={!workspaceChoice || clayBusy} onClick={() => clayAction("switch", { workspace_id: workspaceChoice })}>Utiliser</Button><Button variant="signal" disabled={!clay?.active.user_id || clayBusy} onClick={() => clayAction("pin")}>Confirmer ce compte <Check /></Button></div></div></div>
              <div className="clay-step"><span className="step-no">3</span><div><h3>Définir la table de destination</h3><p>Créez une source Webhook d’entrée dans la table Clay, puis collez son URL ici. Elle reste sur cette machine.</p><div className="flex flex-wrap gap-2 mt-4"><Select value={clayTable} onValueChange={value => { setClayTable(value); setClayPreview(null) }}><SelectTrigger className="w-[190px]" aria-label="Table Clay cible"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="matches">Matchs ICP</SelectItem><SelectItem value="participants">Participants</SelectItem><SelectItem value="accounts">Entreprises</SelectItem><SelectItem value="evidence">Preuves</SelectItem></SelectContent></Select><Input type="password" className="min-w-[250px] flex-1" aria-label="URL du webhook Clay" placeholder="https://…clay.com/…" autoComplete="off" value={webhook} onChange={event => setWebhook(event.target.value)} /><Button variant="outline" disabled={!webhook || !clay?.pinned.user_id || clayBusy} onClick={() => clayAction("webhook", { table: clayTable, url: webhook })}>Enregistrer</Button></div><p className="field-note mt-3">Tables configurées : {clay?.configured_tables.length ? clay.configured_tables.join(", ") : "aucune"}.</p></div></div>
            </div>
            <Card className="border-[#d7dcad]"><CardHeader><CardTitle>Prévisualiser, puis envoyer</CardTitle><CardDescription>Transport Clay par webhook : ajoute des lignes; ne remplace pas une table existante.</CardDescription></CardHeader><CardContent><div className="flex flex-wrap items-center gap-3"><Button variant="outline" disabled={!run || !clay?.configured_tables.includes(clayTable) || clayBusy} onClick={() => clayAction("push", { run_id: run?.run_id, table: clayTable, apply: false })}>Prévisualiser l’envoi</Button><Button variant="signal" disabled={!clayPreview || clayPreview.runId !== run?.run_id || clayPreview.table !== clayTable || clayPreview.pending === 0 || clayBusy} onClick={() => clayAction("push", { run_id: run?.run_id, table: clayTable, apply: true })}>Envoyer {clayPreview?.pending || 0} lignes <ArrowRight /></Button></div>{clayPreview && <div className="mt-5 grid gap-3 sm:grid-cols-3"><div className="detail-block"><dt>Lignes à envoyer</dt><dd className="text-lg font-semibold">{formatNumber(clayPreview.pending)}</dd></div><div className="detail-block"><dt>Déjà envoyées</dt><dd className="text-lg font-semibold">{formatNumber(clayPreview.already_sent)}</dd></div><div className="detail-block"><dt>Destination</dt><dd className="mono text-xs">…{clayPreview.destination_fingerprint}</dd></div></div>}{clayMessage && <p className="field-note mt-4">{clayMessage}</p>}{!run && <p className="field-note mt-3">Lancez d’abord une analyse pour préparer les fichiers à envoyer.</p>}</CardContent></Card>
          </div>
        </>}
      </div>
    </main>
    <Dialog open={!!selected} onOpenChange={open => { if (!open) setSelected(null) }}><DialogContent><DialogHeader><DialogTitle>{selected?.person_name || "Participant"}</DialogTitle><DialogDescription>{selected?.job_title || "Poste à confirmer"} · {selected?.company_name || "Entreprise à confirmer"}</DialogDescription></DialogHeader>{selected && <div className="grid gap-4"><div className="flex flex-wrap items-center gap-2">{fitBadge(selected.fit_status)}<Badge variant="muted">{selected.client_name}</Badge><span className="text-xs text-[#72726c] ml-auto">Priorité {selected.priority_score}/100</span></div><div className="detail-grid"><div className="detail-block"><dt>Pourquoi participer ?</dt><dd>{selected.why_attend || "À confirmer"}</dd></div><div className="detail-block"><dt>Objectif d’affaires</dt><dd>{selected.business_objective || "À confirmer"}</dd></div><div className="detail-block"><dt>Raison du match</dt><dd>{splitPipe(selected.fit_reasons).length ? splitPipe(selected.fit_reasons).join(" · ") : "Aucune réserve documentée"}</dd></div><div className="detail-block"><dt>Angle pour {selected.client_name}</dt><dd>{selected.opportunity_hypothesis}</dd></div></div>{selected.exclusion_reasons && <div className="rounded-lg bg-[#f7ece9] p-4 text-sm"><strong>Exclusions :</strong> {splitPipe(selected.exclusion_reasons).join(" · ")}</div>}<div className="rounded-lg bg-white border border-[#e5e3dd] p-4"><div className="text-xs uppercase tracking-wider font-bold text-[#777770] mb-2">Question de découverte</div><p className="text-sm leading-6 m-0">{selected.next_question}</p></div><div className="text-xs text-[#777770]"><strong>Sources :</strong> {splitPipe(selected.evidence_urls).length ? splitPipe(selected.evidence_urls).filter(url => /^https?:\/\//.test(url)).map(url => <a key={url} href={url} target="_blank" rel="noreferrer" className="block underline break-all mt-1">{url}</a>) : "Aucune preuve externe liée à cette ligne."}</div></div>}</DialogContent></Dialog>
  </div>
}

export default App
