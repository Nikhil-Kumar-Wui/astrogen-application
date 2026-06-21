import { useState, useEffect } from "react";
import { X, Zap, ExternalLink, CheckCircle, Loader2, AlertCircle, Cpu, ChevronRight } from "lucide-react";

const API = "http://localhost:8001";

interface KagglePopupProps {
  onClose: () => void;
}

type Step = "intro" | "paste" | "connecting" | "success";

export function KagglePopup({ onClose }: KagglePopupProps) {
  const [step, setStep] = useState<Step>("intro");
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [connecting, setConnecting] = useState(false);

  const handleConnect = async () => {
    setError("");
    if (!url.trim()) { setError("Please paste the tunnel URL first."); return; }
    if (!url.startsWith("http")) { setError("URL must start with https://"); return; }
    setConnecting(true);
    setStep("connecting");
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
      setStep("paste");
    } finally {
      setConnecting(false);
    }
  };

  const handleLaunchKaggle = () => {
    window.open("https://www.kaggle.com/code/nikhilwui/astrogen-gpu-launcher", "_blank");
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
        <div className="flex items-center gap-2 px-6 py-3">
          {(["intro", "paste", "success"] as const).map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all" style={{
                background: step === s || (s === "paste" && step === "connecting") || (s === "intro" && ["paste","connecting","success"].includes(step)) || (s === "paste" && step === "success")
                  ? "rgba(99,102,241,0.9)" : "rgba(255,255,255,0.06)",
                color: step === s ? "#fff" : "#475569",
                border: step === s ? "none" : "1px solid rgba(255,255,255,0.08)",
              }}>{step === "success" && s === "paste" ? <CheckCircle size={12} /> : i + 1}</div>
              {i < 2 && <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.06)", width: 32 }} />}
            </div>
          ))}
        </div>

        {/* Content */}
        <div className="px-6 pb-6 space-y-4">
          {step === "intro" && (
            <>
              <div>
                <h2 className="text-white font-bold text-lg mb-1">Use Free Kaggle GPU</h2>
                <p className="text-sm leading-relaxed" style={{ color: "#94a3b8" }}>
                  Generate images up to <span className="font-semibold text-white">10× faster</span> using Kaggle's free T4 GPU.
                  No cost, no setup — just click Launch, then paste the URL here.
                </p>
              </div>

              <div className="rounded-xl p-4 space-y-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                {[
                  { icon: "1", text: "Click Launch Kaggle Notebook below" },
                  { icon: "2", text: "Run all cells in the notebook (takes ~2 min)" },
                  { icon: "3", text: "Copy the Pinggy URL that appears" },
                  { icon: "4", text: "Paste it here and click Connect" },
                ].map(item => (
                  <div key={item.icon} className="flex items-start gap-3">
                    <div className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5" style={{ background: "rgba(99,102,241,0.2)", color: "#818cf8" }}>{item.icon}</div>
                    <p className="text-sm" style={{ color: "#94a3b8" }}>{item.text}</p>
                  </div>
                ))}
              </div>

              <div className="flex gap-3 pt-2">
                <button onClick={handleLaunchKaggle}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm transition-all"
                  style={{ background: "rgba(32,190,255,0.12)", border: "1px solid rgba(32,190,255,0.25)", color: "#20BEFF" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "rgba(32,190,255,0.2)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "rgba(32,190,255,0.12)")}
                >
                  <ExternalLink size={14} /> Launch Kaggle Notebook
                </button>
                <button onClick={() => setStep("paste")}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm transition-all"
                  style={{ background: "rgba(99,102,241,0.9)", color: "#fff" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "rgba(99,102,241,1)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "rgba(99,102,241,0.9)")}
                >
                  I have the URL <ChevronRight size={14} />
                </button>
              </div>

              <p className="text-xs text-center" style={{ color: "#334155" }}>
                Your model weights stay private. Kaggle only runs inference.
              </p>
            </>
          )}

          {(step === "paste" || step === "connecting") && (
            <>
              <div>
                <h2 className="text-white font-bold text-lg mb-1">Paste Tunnel URL</h2>
                <p className="text-sm" style={{ color: "#94a3b8" }}>
                  Paste the Pinggy / ngrok URL from the Kaggle notebook output.
                </p>
              </div>

              <div>
                <input
                  type="url"
                  value={url}
                  onChange={e => { setUrl(e.target.value); setError(""); }}
                  placeholder="https://abc123.a.pinggy.io"
                  className="w-full rounded-xl px-4 py-3 text-sm outline-none transition-all"
                  style={{
                    background: "rgba(255,255,255,0.04)",
                    border: error ? "1px solid rgba(239,68,68,0.5)" : "1px solid rgba(255,255,255,0.1)",
                    color: "#e2e8f0",
                    fontFamily: "monospace",
                  }}
                  disabled={step === "connecting"}
                  onFocus={e => !error && (e.target.style.border = "1px solid rgba(99,102,241,0.6)")}
                  onBlur={e => !error && (e.target.style.border = "1px solid rgba(255,255,255,0.1)")}
                />
                {error && <p className="text-xs mt-1.5 flex items-center gap-1" style={{ color: "#f87171" }}><AlertCircle size={11} />{error}</p>}
              </div>

              <div className="flex gap-3 pt-1">
                <button onClick={() => setStep("intro")} disabled={step === "connecting"}
                  className="px-4 py-2.5 rounded-xl text-sm transition-all"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#64748b" }}
                >
                  Back
                </button>
                <button onClick={handleConnect} disabled={step === "connecting"}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm transition-all"
                  style={{ background: step === "connecting" ? "rgba(99,102,241,0.5)" : "rgba(99,102,241,0.9)", color: "#fff" }}
                >
                  {step === "connecting" ? <><Loader2 size={14} className="animate-spin" /> Connecting...</> : "Connect GPU"}
                </button>
              </div>
            </>
          )}

          {step === "success" && (
            <div className="text-center py-4 space-y-4">
              <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto" style={{ background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)" }}>
                <CheckCircle size={28} style={{ color: "#10b981" }} />
              </div>
              <div>
                <h2 className="text-white font-bold text-lg">GPU Connected!</h2>
                <p className="text-sm mt-1" style={{ color: "#94a3b8" }}>
                  AstroGen will now generate images using Kaggle T4 GPU.
                  You can disconnect anytime from the Profile panel.
                </p>
              </div>
              <button onClick={onClose}
                className="w-full py-2.5 rounded-xl font-semibold text-sm"
                style={{ background: "rgba(99,102,241,0.9)", color: "#fff" }}
              >
                Start Generating ✦
              </button>
            </div>
          )}
        </div>

        {/* Footer — skip */}
        {(step === "intro" || step === "paste") && (
          <div className="px-6 pb-4 text-center">
            <button onClick={onClose} className="text-xs transition-colors" style={{ color: "#334155" }}
              onMouseEnter={e => (e.currentTarget.style.color = "#64748b")}
              onMouseLeave={e => (e.currentTarget.style.color = "#334155")}
            >
              Skip for now — use local CPU
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
