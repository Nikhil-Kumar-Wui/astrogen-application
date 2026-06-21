import { useState, useEffect, useRef } from "react";
import {
  X, User, Zap, Cpu, Wifi, WifiOff, Key, ExternalLink,
  CheckCircle, AlertCircle, Loader2, LogOut, Settings, ChevronRight
} from "lucide-react";

const API = "http://localhost:8001";

interface ProfilePanelProps {
  onClose: () => void;
  onOpenKagglePopup?: () => void;
}

interface SettingsData {
  gemini_api_key: string;
  gemini_api_key_set: boolean;
  backend: string;
  kaggle_connected: boolean;
  kaggle_url: string;
  launch_count: number;
}

export function ProfilePanel({ onClose, onOpenKagglePopup }: ProfilePanelProps) {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [geminiKey, setGeminiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "success" | "error">("idle");
  const [disconnecting, setDisconnecting] = useState(false);
  const [kaggleReachable, setKaggleReachable] = useState<boolean | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Load settings on mount
  useEffect(() => {
    fetchSettings();
  }, []);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    setTimeout(() => document.addEventListener("mousedown", handler), 100);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API}/settings`);
      const data = await res.json();
      setSettings(data);
      // Also check kaggle reachability
      if (data.kaggle_connected) {
        checkKaggle();
      }
    } catch {
      setSettings(null);
    }
  };

  const checkKaggle = async () => {
    try {
      const res = await fetch(`${API}/kaggle/status`);
      const data = await res.json();
      setKaggleReachable(data.reachable);
    } catch {
      setKaggleReachable(false);
    }
  };

  const handleSaveKey = async () => {
    if (!geminiKey.trim()) return;
    setSaving(true);
    setSaveStatus("idle");
    try {
      const res = await fetch(`${API}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gemini_api_key: geminiKey.trim() }),
      });
      if (!res.ok) throw new Error();
      setSaveStatus("success");
      setGeminiKey("");
      fetchSettings();
      setTimeout(() => setSaveStatus("idle"), 2500);
    } catch {
      setSaveStatus("error");
    } finally {
      setSaving(false);
    }
  };

  const handleDisconnect = async () => {
    setDisconnecting(true);
    try {
      await fetch(`${API}/kaggle/url`, { method: "DELETE" });
      fetchSettings();
      setKaggleReachable(null);
    } catch {}
    setDisconnecting(false);
  };

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40" style={{ background: "rgba(0,0,0,0.4)" }} />

      {/* Panel */}
      <div
        ref={panelRef}
        className="fixed right-0 top-0 h-full z-50 w-80 flex flex-col overflow-hidden"
        style={{
          background: "linear-gradient(180deg, #080b18 0%, #06080f 100%)",
          borderLeft: "1px solid rgba(255,255,255,0.06)",
          boxShadow: "-24px 0 80px rgba(0,0,0,0.6)",
          animation: "slideInRight 0.22s cubic-bezier(0.16,1,0.3,1)",
        }}
      >
        <style>{`
          @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to   { transform: translateX(0);    opacity: 1; }
          }
        `}</style>

        {/* ── Header ────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-5 py-4 flex-shrink-0" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
              <User size={18} color="#fff" />
            </div>
            <div>
              <p className="text-white font-semibold text-sm">Profile</p>
              <p className="text-xs" style={{ color: "#475569" }}>AstroGen Settings</p>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
            style={{ color: "#475569", border: "1px solid rgba(255,255,255,0.06)" }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.06)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          >
            <X size={14} />
          </button>
        </div>

        {/* ── Content ───────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">

          {/* ── GPU Status Card ─────────────────────────────── */}
          <div className="rounded-xl p-4 space-y-3" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
            <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#475569" }}>Generation Backend</p>

            {settings?.kaggle_connected ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{
                      background: kaggleReachable === true ? "#10b981" : kaggleReachable === false ? "#ef4444" : "#f59e0b",
                      boxShadow: kaggleReachable === true ? "0 0 6px #10b981" : "none",
                    }} />
                    <span className="text-sm font-medium text-white">Kaggle GPU</span>
                    <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(32,190,255,0.1)", color: "#20BEFF", border: "1px solid rgba(32,190,255,0.2)" }}>T4 × 2</span>
                  </div>
                  {kaggleReachable === null && <Loader2 size={12} className="animate-spin" style={{ color: "#475569" }} />}
                  {kaggleReachable === true && <CheckCircle size={12} style={{ color: "#10b981" }} />}
                  {kaggleReachable === false && <AlertCircle size={12} style={{ color: "#ef4444" }} />}
                </div>

                {settings.kaggle_url && (
                  <p className="text-xs truncate font-mono px-2 py-1.5 rounded" style={{ color: "#64748b", background: "rgba(0,0,0,0.3)" }}>
                    {settings.kaggle_url}
                  </p>
                )}

                {kaggleReachable === false && (
                  <p className="text-xs" style={{ color: "#f87171" }}>
                    GPU session may have expired. Launch a new Kaggle notebook and reconnect.
                  </p>
                )}

                <div className="flex gap-2">
                  <button onClick={() => onOpenKagglePopup?.()}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-all"
                    style={{ background: "rgba(32,190,255,0.1)", border: "1px solid rgba(32,190,255,0.2)", color: "#20BEFF" }}
                    onMouseEnter={e => (e.currentTarget.style.background = "rgba(32,190,255,0.18)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "rgba(32,190,255,0.1)")}
                  >
                    <Zap size={11} /> Reconnect
                  </button>
                  <button onClick={handleDisconnect} disabled={disconnecting}
                    className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-all"
                    style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.15)", color: "#f87171" }}
                    onMouseEnter={e => (e.currentTarget.style.background = "rgba(239,68,68,0.15)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "rgba(239,68,68,0.08)")}
                  >
                    {disconnecting ? <Loader2 size={11} className="animate-spin" /> : <LogOut size={11} />}
                    {disconnecting ? "..." : "Disconnect"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ background: "#f59e0b" }} />
                  <span className="text-sm font-medium text-white">Local CPU</span>
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.2)" }}>Slow</span>
                </div>
                <p className="text-xs" style={{ color: "#64748b" }}>
                  Connect Kaggle GPU for faster generation. Free T4 × 2 GPUs.
                </p>
                <button onClick={() => onOpenKagglePopup?.()}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all"
                  style={{ background: "linear-gradient(135deg, rgba(99,102,241,0.15), rgba(32,190,255,0.1))", border: "1px solid rgba(99,102,241,0.25)", color: "#818cf8" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "linear-gradient(135deg, rgba(99,102,241,0.25), rgba(32,190,255,0.15))")}
                  onMouseLeave={e => (e.currentTarget.style.background = "linear-gradient(135deg, rgba(99,102,241,0.15), rgba(32,190,255,0.1))")}
                >
                  <Zap size={14} /> Launch Kaggle GPU
                </button>
              </div>
            )}
          </div>

          {/* ── Gemini API Key ──────────────────────────────── */}
          <div className="rounded-xl p-4 space-y-3" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#475569" }}>Gemini API Key</p>
              {settings?.gemini_api_key_set && (
                <div className="flex items-center gap-1 text-xs" style={{ color: "#10b981" }}>
                  <CheckCircle size={11} /> Set
                </div>
              )}
            </div>

            {settings?.gemini_api_key_set && (
              <p className="text-xs font-mono px-2 py-1.5 rounded" style={{ color: "#475569", background: "rgba(0,0,0,0.3)" }}>
                {settings.gemini_api_key}
              </p>
            )}

            <div className="space-y-2">
              <input
                type="password"
                value={geminiKey}
                onChange={e => { setGeminiKey(e.target.value); setSaveStatus("idle"); }}
                placeholder={settings?.gemini_api_key_set ? "Update key..." : "Paste your Gemini API key"}
                className="w-full rounded-lg px-3 py-2.5 text-xs outline-none transition-all"
                style={{
                  background: "rgba(255,255,255,0.04)",
                  border: saveStatus === "error" ? "1px solid rgba(239,68,68,0.4)" : "1px solid rgba(255,255,255,0.08)",
                  color: "#e2e8f0",
                  fontFamily: "monospace",
                }}
                onFocus={e => (e.target.style.border = "1px solid rgba(99,102,241,0.5)")}
                onBlur={e => (e.target.style.border = saveStatus === "error" ? "1px solid rgba(239,68,68,0.4)" : "1px solid rgba(255,255,255,0.08)")}
                onKeyDown={e => e.key === "Enter" && handleSaveKey()}
              />
              <div className="flex items-center gap-2">
                <button onClick={handleSaveKey} disabled={saving || !geminiKey.trim()}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-all"
                  style={{
                    background: !geminiKey.trim() ? "rgba(255,255,255,0.04)" : "rgba(99,102,241,0.9)",
                    color: !geminiKey.trim() ? "#475569" : "#fff",
                    cursor: !geminiKey.trim() ? "not-allowed" : "pointer",
                  }}
                >
                  {saving ? <Loader2 size={11} className="animate-spin" /> : <Key size={11} />}
                  {saving ? "Saving..." : "Save Key"}
                </button>
                <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer"
                  className="flex items-center justify-center gap-1 px-3 py-2 rounded-lg text-xs transition-all"
                  style={{ color: "#475569", border: "1px solid rgba(255,255,255,0.06)" }}
                  onMouseEnter={e => (e.currentTarget.style.color = "#94a3b8")}
                  onMouseLeave={e => (e.currentTarget.style.color = "#475569")}
                >
                  <ExternalLink size={10} /> Get key
                </a>
              </div>
              {saveStatus === "success" && <p className="text-xs flex items-center gap-1" style={{ color: "#10b981" }}><CheckCircle size={11} /> Key saved!</p>}
              {saveStatus === "error" && <p className="text-xs flex items-center gap-1" style={{ color: "#f87171" }}><AlertCircle size={11} /> Failed to save.</p>}
            </div>
          </div>

          {/* ── Stats ──────────────────────────────────────── */}
          {settings && (
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: "Sessions", value: settings.launch_count, icon: <Zap size={12} /> },
                { label: "Backend", value: settings.backend?.toUpperCase(), icon: settings.backend === "cuda" ? <Zap size={12} /> : <Cpu size={12} /> },
              ].map(stat => (
                <div key={stat.label} className="rounded-xl p-3 flex flex-col gap-1" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div className="flex items-center gap-1.5" style={{ color: "#475569" }}>
                    {stat.icon}
                    <span className="text-xs">{stat.label}</span>
                  </div>
                  <p className="text-sm font-semibold text-white">{stat.value}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Footer ──────────────────────────────────────── */}
        <div className="px-5 py-4 flex-shrink-0" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <p className="text-xs text-center" style={{ color: "#1e293b" }}>
            AstroGen Space Studio • Local
          </p>
        </div>
      </div>
    </>
  );
}
