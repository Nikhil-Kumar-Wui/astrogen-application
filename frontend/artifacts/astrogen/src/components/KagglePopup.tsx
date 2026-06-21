import { useState, useEffect, useRef } from "react";
import { X, Zap, ExternalLink, CheckCircle, Loader2, AlertCircle, Cpu, ChevronRight, Key, ArrowRight } from "lucide-react";

const API = "http://localhost:8001";

interface KagglePopupProps {
  onClose: () => void;
}

type Step = "intro" | "credentials" | "launching" | "paste" | "success";

export function KagglePopup({ onClose }: KagglePopupProps) {
  const [step, setStep] = useState<Step>("intro");
  
  // Credentials
  const [username, setUsername] = useState("");
  const [kaggleKey, setKaggleKey] = useState("");
  
  // Status/URL
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [connecting, setConnecting] = useState(false);
  
  // Auto-Launch State
  const [sessionToken, setSessionToken] = useState("");
  const [launchStatus, setLaunchStatus] = useState("Initializing push request...");
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch saved credentials on load to pre-fill
  useEffect(() => {
    fetch(`${API}/settings`)
      .then(r => r.json())
      .then(d => {
        if (d.kaggle_username) setUsername(d.kaggle_username);
        // We don't pre-fill the key for security, but we know it might be set
      })
      .catch(() => {});
      
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  const handleLaunchKaggleNotebook = () => {
    window.open("https://www.kaggle.com/code/nikhilwui/astrogen-gpu-launcher", "_blank");
  };

  const handleLaunchKaggleApiKey = () => {
    window.open("https://www.kaggle.com/settings", "_blank");
  };

  // ── Manual Connect ──
  const handleConnect = async () => {
    setError("");
    if (!url.trim()) { setError("Please paste the tunnel URL first."); return; }
    if (!url.trim().startsWith("http")) { setError("URL must start with http:// or https://"); return; }
    setConnecting(true);
    try {
      const res = await fetch(`${API}/kaggle/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Failed");
      setStep("success");
    } catch (e: any) {
      setError(e.message || "Could not connect. Check the URL and try again.");
    } finally {
      setConnecting(false);
    }
  };

  // ── Auto-Launch via API ──
  const handleStartAutoLaunch = async () => {
    setError("");
    if (!username.trim() || !kaggleKey.trim()) {
      setError("Both Kaggle Username and API Key are required.");
      return;
    }
    setConnecting(true);
    setStep("launching");
    setLaunchStatus("Connecting to Kaggle API & pushing launcher...");
    
    try {
      const res = await fetch(`${API}/kaggle/launch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: username.trim(),
          key: kaggleKey.trim()
        }),
      });
      
      if (!res.ok) {
        const errDetail = (await res.json()).detail || "Failed to push launcher to Kaggle.";
        throw new Error(errDetail);
      }
      
      const data = await res.json();
      setSessionToken(data.session_token);
      setLaunchStatus("Kernel pushed successfully. Starting remote GPU server...");
      
      // Start polling for URL
      startPolling(data.session_token);
    } catch (e: any) {
      setError(e.message || "Failed to start Kaggle GPU Server.");
      setStep("credentials");
      setConnecting(false);
    }
  };

  const startPolling = (token: string) => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    
    let attempts = 0;
    pollTimerRef.current = setInterval(async () => {
      attempts++;
      try {
        const res = await fetch(`${API}/kaggle/poll?token=${token}&username=${encodeURIComponent(username)}&key=${encodeURIComponent(kaggleKey)}`);
        if (!res.ok) throw new Error("Poll request failed");
        
        const data = await res.json();
        if (data.status === "success") {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          setStep("success");
          setConnecting(false);
        } else if (data.status === "failed") {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          setError(data.detail || "Kaggle server reported an execution error.");
          setStep("credentials");
          setConnecting(false);
        } else {
          // Still waiting
          setLaunchStatus(data.detail || `Waiting for GPU tunnel connection... (${attempts * 5}s)`);
        }
      } catch (e) {
        // Ignore single fetch failures and continue polling
      }
      
      // Timeout after 4 minutes (48 checks)
      if (attempts >= 48) {
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        setError("Connection timeout. The server took too long to boot. You can check the logs on Kaggle or switch to manual input.");
        setStep("credentials");
        setConnecting(false);
      }
    }, 5000);
  };

  const handleCancelAutoLaunch = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
    }
    setConnecting(false);
    setStep("intro");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.85)" }}>
      <div
        className="relative w-full max-w-lg rounded-2xl overflow-hidden"
        style={{
          background: "linear-gradient(135deg, #0a0b1a 0%, #0d1121 100%)",
          border: "1px solid rgba(99,102,241,0.25)",
          boxShadow: "0 0 80px rgba(99,102,241,0.15), 0 24px 80px rgba(0,0,0,0.8)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: "rgba(32,190,255,0.12)", border: "1px solid rgba(32,190,255,0.25)" }}>
              <Zap size={16} style={{ color: "#20BEFF" }} />
            </div>
            <div>
              <p className="text-white font-semibold text-sm">Kaggle GPU Acceleration</p>
              <p className="text-xs" style={{ color: "#64748b" }}>T4 × 2 GPUs — Free</p>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors" style={{ color: "#475569" }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.06)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          >
            <X size={16} />
          </button>
        </div>

        {/* Steps indicator */}
        <div className="flex items-center gap-2 px-6 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.02)" }}>
          {[
            { id: "intro", label: "Overview" },
            { id: "credentials", label: "Setup API" },
            { id: "success", label: "Connected" }
          ].map((s, i) => {
            const isActive = step === s.id || (s.id === "credentials" && (step === "launching" || step === "paste"));
            const isCompleted = step === "success" || (s.id === "intro" && step !== "intro");
            return (
              <div key={s.id} className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all" style={{
                  background: isActive ? "rgba(99,102,241,0.9)" : isCompleted ? "rgba(16,185,129,0.2)" : "rgba(255,255,255,0.04)",
                  color: isActive ? "#fff" : isCompleted ? "#10b981" : "#475569",
                  border: isActive ? "none" : isCompleted ? "1px solid rgba(16,185,129,0.3)" : "1px solid rgba(255,255,255,0.06)",
                }}>
                  {isCompleted ? <CheckCircle size={10} /> : i + 1}
                </div>
                <span className="text-xs font-medium" style={{ color: isActive ? "#fff" : isCompleted ? "#10b981" : "#475569" }}>{s.label}</span>
                {i < 2 && <div className="h-px bg-white/5 w-8" />}
              </div>
            );
          })}
        </div>

        {/* Content */}
        <div className="px-6 pb-6 pt-4 space-y-4">
          
          {/* ── Step 1: Intro ── */}
          {step === "intro" && (
            <>
              <div>
                <h2 className="text-white font-bold text-lg mb-1">Select Connection Mode</h2>
                <p className="text-sm leading-relaxed" style={{ color: "#94a3b8" }}>
                  AstroGen uses heavy astronomical deep learning models (Stable Diffusion, BLIP2, VAE-GAN). Connect to a free cloud GPU server to generate images <span className="font-semibold text-white">10× faster</span>.
                </p>
              </div>

              <div className="space-y-3 pt-2">
                {/* Mode 1: Auto-launch */}
                <button
                  onClick={() => setStep("credentials")}
                  className="w-full text-left p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04] hover:border-indigo-500/40 transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 group-hover:bg-indigo-500/20 transition-all shrink-0">
                      <Cpu size={15} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-white">Auto-Launch GPU Server (Recommended)</p>
                        <ArrowRight size={14} className="text-indigo-400 group-hover:translate-x-1 transition-transform" />
                      </div>
                      <p className="text-xs mt-1" style={{ color: "#64748b" }}>
                        Enter your Kaggle API key once. The app will automatically build, deploy, and launch the GPU server for you. No manual console work.
                      </p>
                    </div>
                  </div>
                </button>

                {/* Mode 2: Manual paste */}
                <button
                  onClick={() => setStep("paste")}
                  className="w-full text-left p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04] hover:border-sky-500/30 transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-sky-500/10 border border-sky-500/20 text-sky-400 group-hover:bg-sky-500/20 transition-all shrink-0">
                      <ExternalLink size={15} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-white">Manual Connection / Link paste</p>
                        <ArrowRight size={14} className="text-sky-400 group-hover:translate-x-1 transition-transform" />
                      </div>
                      <p className="text-xs mt-1" style={{ color: "#64748b" }}>
                        Open our notebook on Kaggle, click "Run All" yourself, wait for it to generate a Pinggy URL, and paste it here manually.
                      </p>
                    </div>
                  </div>
                </button>
              </div>

              <div className="pt-2 text-center">
                <button onClick={onClose} className="text-xs hover:text-white transition-colors" style={{ color: "#475569" }}>
                  Skip for now — use local CPU (very slow)
                </button>
              </div>
            </>
          )}

          {/* ── Step 2: Credentials Input ── */}
          {step === "credentials" && (
            <>
              <div>
                <h2 className="text-white font-bold text-lg mb-1">Kaggle API Credentials</h2>
                <p className="text-xs" style={{ color: "#94a3b8" }}>
                  We need your Kaggle API username and token to push the launch script.
                  Don't have them? Click <button onClick={handleLaunchKaggleApiKey} className="text-indigo-400 underline font-semibold">Get API Token</button> to generate it under "API" on Kaggle settings page.
                </p>
              </div>

              <div className="space-y-3 pt-1">
                {/* Username */}
                <div className="space-y-1">
                  <label className="text-[10px] uppercase tracking-widest font-mono text-zinc-500">Kaggle Username</label>
                  <input
                    type="text"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    placeholder="e.g. nikhilwui"
                    className="w-full rounded-xl px-4 py-2.5 text-xs outline-none transition-all"
                    style={{
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      color: "#e2e8f0",
                    }}
                    onFocus={e => (e.target.style.border = "1px solid rgba(99,102,241,0.5)")}
                    onBlur={e => (e.target.style.border = "1px solid rgba(255,255,255,0.08)")}
                  />
                </div>

                {/* API Key */}
                <div className="space-y-1">
                  <label className="text-[10px] uppercase tracking-widest font-mono text-zinc-500">Kaggle API Key (from kaggle.json)</label>
                  <input
                    type="password"
                    value={kaggleKey}
                    onChange={e => setKaggleKey(e.target.value)}
                    placeholder="Paste the 'key' value from your downloaded kaggle.json"
                    className="w-full rounded-xl px-4 py-2.5 text-xs outline-none transition-all font-mono"
                    style={{
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      color: "#e2e8f0",
                    }}
                    onFocus={e => (e.target.style.border = "1px solid rgba(99,102,241,0.5)")}
                    onBlur={e => (e.target.style.border = "1px solid rgba(255,255,255,0.08)")}
                  />
                </div>

                {error && (
                  <div className="space-y-2">
                    <p className="text-xs text-red-400 flex items-center gap-1.5 pt-1">
                      <AlertCircle size={12} /> {error}
                    </p>
                    <div className="text-[11px] leading-relaxed rounded-xl p-3 border border-red-500/15 bg-red-500/5 space-y-1" style={{ color: "#94a3b8" }}>
                      <p className="font-semibold text-zinc-300">Common troubleshooting steps:</p>
                      <p>1. Make sure your Kaggle account is <strong>phone-verified</strong> (on Kaggle settings page) — required to access GPUs and run API scripts.</p>
                      <p>2. Ensure you copied the exact, long <strong>"key"</strong> string from your downloaded <code>kaggle.json</code>, not your password.</p>
                      <p>3. If auto-launch continues to fail, click <strong>Back</strong> and select <strong>Manual Connection</strong> to run the server in your web browser.</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-3 pt-2">
                <button onClick={() => setStep("intro")}
                  className="px-4 py-2.5 rounded-xl text-sm transition-all"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#64748b" }}
                >
                  Back
                </button>
                <button
                  onClick={handleStartAutoLaunch}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm transition-all"
                  style={{ background: "rgba(99,102,241,0.9)", color: "#fff" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "rgba(99,102,241,1)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "rgba(99,102,241,0.9)")}
                >
                  <Cpu size={14} /> Deploy & Start GPU Server
                </button>
              </div>
            </>
          )}

          {/* ── Step 3: Launching Loader ── */}
          {step === "launching" && (
            <div className="text-center py-6 space-y-4">
              <Loader2 size={36} className="animate-spin text-indigo-400 mx-auto" />
              <div>
                <h3 className="text-white font-bold text-lg">Launching GPU Server</h3>
                <p className="text-xs mt-1 max-w-sm mx-auto" style={{ color: "#94a3b8" }}>
                  {launchStatus}
                </p>
                <p className="text-[10px] mt-3" style={{ color: "#475569" }}>
                  This takes 1.5 - 2 minutes on first run as Kaggle installs requirements.
                </p>
              </div>

              <div className="pt-2">
                <button onClick={handleCancelAutoLaunch}
                  className="px-5 py-2 rounded-xl text-xs transition-all"
                  style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", color: "#f87171" }}
                >
                  Cancel & Stop
                </button>
              </div>
            </div>
          )}

          {/* ── Step 4: Manual Paste Input ── */}
          {step === "paste" && (
            <>
              <div>
                <h2 className="text-white font-bold text-lg mb-1">Paste Tunnel URL</h2>
                <p className="text-xs leading-relaxed" style={{ color: "#94a3b8" }}>
                  1. Click <button onClick={handleLaunchKaggleNotebook} className="text-indigo-400 underline font-semibold">Launch Kaggle Notebook</button>.<br />
                  2. In Kaggle, click **Run All** (under "Run" menu). It takes ~2 mins.<br />
                  3. Find the URL printed in the output (e.g. `https://*.pinggy.link`).<br />
                  4. Paste it below and click **Connect**.
                </p>
              </div>

              <div className="space-y-2 pt-1">
                <input
                  type="url"
                  value={url}
                  onChange={e => { setUrl(e.target.value); setError(""); }}
                  placeholder="https://xyz123.a.pinggy.link"
                  className="w-full rounded-xl px-4 py-3 text-xs outline-none transition-all font-mono"
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: error ? "1px solid rgba(239,68,68,0.5)" : "1px solid rgba(255,255,255,0.08)",
                    color: "#e2e8f0",
                  }}
                  onFocus={e => !error && (e.target.style.border = "1px solid rgba(99,102,241,0.5)")}
                  onBlur={e => !error && (e.target.style.border = "1px solid rgba(255,255,255,0.08)")}
                />
                {error && (
                  <p className="text-xs text-red-400 flex items-center gap-1.5">
                    <AlertCircle size={12} /> {error}
                  </p>
                )}
              </div>

              <div className="flex gap-3 pt-2">
                <button onClick={() => setStep("intro")}
                  className="px-4 py-2.5 rounded-xl text-sm transition-all"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#64748b" }}
                >
                  Back
                </button>
                <button onClick={handleConnect} disabled={connecting}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm transition-all"
                  style={{ background: connecting ? "rgba(99,102,241,0.5)" : "rgba(99,102,241,0.9)", color: "#fff" }}
                >
                  {connecting ? <><Loader2 size={14} className="animate-spin" /> Connecting...</> : "Connect GPU"}
                </button>
              </div>
            </>
          )}

          {/* ── Step 5: Success ── */}
          {step === "success" && (
            <div className="text-center py-6 space-y-4">
              <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto" style={{ background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)" }}>
                <CheckCircle size={28} style={{ color: "#10b981" }} />
              </div>
              <div>
                <h2 className="text-white font-bold text-lg">GPU Server Connected!</h2>
                <p className="text-sm mt-1" style={{ color: "#94a3b8" }}>
                  AstroGen is now connected to the remote Kaggle T4 GPU.
                  Generating deep space imagery will be incredibly fast.
                </p>
              </div>
              <button onClick={onClose}
                className="w-full py-2.5 rounded-xl font-semibold text-sm transition-all"
                style={{ background: "rgba(99,102,241,0.9)", color: "#fff" }}
                onMouseEnter={e => (e.currentTarget.style.background = "rgba(99,102,241,1)")}
                onMouseLeave={e => (e.currentTarget.style.background = "rgba(99,102,241,0.9)")}
              >
                Begin Studio Session ✦
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
