import { useRef, useEffect, useState } from "react";
import { Link, useLocation } from "wouter";
import { Starfield } from "@/components/Starfield";
import { Button } from "@/components/ui/button";
import { useGetStatus } from "@workspace/api-client-react";
import { ProfilePanel } from "@/components/ProfilePanel";
import { KagglePopup } from "@/components/KagglePopup";

import {
  Sparkles,
  MessageSquare,
  ScanSearch,
  Info,
  Database,
  Brain,
  Cpu,
  Telescope,
  Image as ImageIcon,
  Activity,
  ArrowRight,
  GitFork,
  Layers,
  Zap,
  BookOpen,
  ChevronRight,
  User,
} from "lucide-react";

function PlanetLogo({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none" aria-hidden>
      <circle cx="16" cy="16" r="5.5" fill="currentColor" />
      <ellipse
        cx="16" cy="16" rx="14" ry="5"
        stroke="currentColor" strokeWidth="1.6" fill="none"
        transform="rotate(-22 16 16)"
      />
    </svg>
  );
}

function useCountUp(target: number, duration = 1800) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const animated = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !animated.current) {
          animated.current = true;
          observer.disconnect();
          const start = performance.now();
          const tick = (now: number) => {
            const t = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - t, 3);
            setCount(Math.round(eased * target));
            if (t < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        }
      },
      { threshold: 0.4 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [target, duration]);

  return { count, ref };
}

function StatItem({ target, suffix = "", label }: { target: number; suffix?: string; label: string }) {
  const { count, ref } = useCountUp(target);
  const display = count >= 1000 ? count.toLocaleString() : count;
  return (
    <div className="flex flex-col items-center text-center gap-1.5 min-w-0">
      <div className="font-display text-2xl sm:text-3xl md:text-3xl lg:text-5xl font-bold text-white tracking-tight">
        <span ref={ref}>{display}</span>
        {suffix}
      </div>
      <div className="text-[10px] text-zinc-500 uppercase tracking-[0.18em] font-mono leading-tight break-words">
        {label}
      </div>
    </div>
  );
}

const STATS = [
  { target: 6984, suffix: "+", label: "Training Images" },
  { target: 9, suffix: "", label: "Astronomy Classes" },
  { target: 3, suffix: "", label: "Deep Learning\nModels" },
  { target: 10000, suffix: "+", label: "Generated Samples" },
  { target: 5, suffix: "", label: "Research Modules" },
  { target: 1, suffix: "", label: "Desktop Platform" },
];

const CAPABILITIES = [
  {
    icon: Sparkles,
    title: "Text-to-Space Generation",
    desc: "Describe any cosmic scene — nebulae, black holes, star clusters — and LoRA Stable Diffusion renders photorealistic astronomical imagery from your prompt.",
    tag: "LoRA SD",
  },
  {
    icon: Layers,
    title: "VAE-GAN Synthesis",
    desc: "Generate structurally-consistent deep space imagery autonomously. The VAE-GAN model creates novel cosmic structures with no prompt required.",
    tag: "VAE-GAN",
  },
  {
    icon: ScanSearch,
    title: "Visual Intelligence",
    desc: "Upload any telescope or satellite image and BLIP-2 will analyze its content, identify celestial objects, and generate detailed scientific captions.",
    tag: "BLIP-2",
  },
  {
    icon: MessageSquare,
    title: "Astrophysics Chat",
    desc: "Have deep conversations about stellar physics, orbital mechanics, cosmology and more. Gemini Pro provides expert-level astronomical knowledge.",
    tag: "Gemini",
  },
  {
    icon: BookOpen,
    title: "Session History",
    desc: "Every generation is saved and organized into research sessions. Revisit past work, compare outputs, and build on previous explorations.",
    tag: "Sessions",
  },
  {
    icon: ImageIcon,
    title: "Image Archive",
    desc: "Browse the full gallery of every image ever generated. Download high-resolution outputs and share your cosmic discoveries.",
    tag: "Gallery",
  },
];

const PIPELINE = [
  { icon: Database, title: "APOD Dataset", desc: "NASA archive" },
  { icon: Brain, title: "LoRA SD", desc: "Fine-tuned diffusion" },
  { icon: Sparkles, title: "VAE-GAN", desc: "Structure refinement" },
  { icon: Telescope, title: "BLIP-2", desc: "Visual grounding" },
  { icon: Cpu, title: "Platform", desc: "Desktop environment" },
];

export default function HomePage() {
  const [, setLocation] = useLocation();
  const { data: status } = useGetStatus({ query: { refetchInterval: 8000 } });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showKaggle, setShowKaggle] = useState(false);
  const [settings, setSettings] = useState<any>(null);

  // Auto-show Kaggle popup on first and every 5th launch if not connected
  useEffect(() => {
    let active = true;
    const checkSettings = () => {
      fetch("http://localhost:8001/settings")
        .then(r => {
          if (!r.ok) throw new Error("not ok");
          return r.json();
        })
        .then(d => {
          if (!active) return;
          setSettings(d);
          if ((d.launch_count === 1 || d.launch_count % 5 === 0) && !d.kaggle_connected) {
            setTimeout(() => {
              if (active) setShowKaggle(true);
            }, 1500);
          }
        })
        .catch(() => {
          if (active) {
            setTimeout(checkSettings, 2000);
          }
        });
    };
    checkSettings();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col relative">
      <Starfield />

      {/* ── Navigation ── */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.06] bg-black/60 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2 text-white">
            <PlanetLogo className="w-5 h-5" />
            <span className="font-display font-bold text-base tracking-wider">
              ASTRO<span className="title-gradient">GEN</span>
            </span>
          </div>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 text-white text-sm font-medium">
              <Sparkles className="w-3.5 h-3.5" /> Home
            </span>
            <Link href="/generate" className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-zinc-400 hover:text-white text-sm transition-colors">
              <MessageSquare className="w-3.5 h-3.5" /> Workspace
            </Link>
            <Link href="/generate" onClick={() => {}} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-zinc-400 hover:text-white text-sm transition-colors">
              <ScanSearch className="w-3.5 h-3.5" /> Analyze
            </Link>
            <a href="#about" className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-zinc-400 hover:text-white text-sm transition-colors">
              <Info className="w-3.5 h-3.5" /> About
            </a>
            {/* Profile button */}
            <button
              onClick={() => setShowProfile(v => !v)}
              className="ml-2 w-8 h-8 rounded-full flex items-center justify-center transition-all overflow-hidden"
              style={{
                background: "#18181b",
                border: "1px solid rgba(255,255,255,0.15)",
                boxShadow: showProfile ? "0 0 12px rgba(255,255,255,0.2)" : "none"
              }}
              aria-label="Profile"
            >
              {settings?.user_picture ? (
                <img src={settings.user_picture} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                <User size={14} color="#fff" />
              )}
            </button>
          </nav>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 text-zinc-400 hover:text-white transition-colors"
            onClick={() => setMobileMenuOpen(v => !v)}
            aria-label="Toggle menu"
          >
            <div className="w-5 flex flex-col gap-1">
              <span className={`block h-px bg-current transition-all ${mobileMenuOpen ? "rotate-45 translate-y-1.5" : ""}`} />
              <span className={`block h-px bg-current transition-all ${mobileMenuOpen ? "opacity-0" : ""}`} />
              <span className={`block h-px bg-current transition-all ${mobileMenuOpen ? "-rotate-45 -translate-y-1.5" : ""}`} />
            </div>
          </button>
        </div>

        {/* Mobile dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-white/[0.06] bg-black/90 backdrop-blur-xl px-4 py-3 flex flex-col gap-1">
            <span className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 text-white text-sm font-medium">
              <Sparkles className="w-4 h-4" /> Home
            </span>
            <Link href="/generate" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2 px-3 py-2 rounded-lg text-zinc-400 text-sm">
              <MessageSquare className="w-4 h-4" /> Workspace
            </Link>
            <a href="#features" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2 px-3 py-2 rounded-lg text-zinc-400 text-sm">
              <ScanSearch className="w-4 h-4" /> Features
            </a>
            <a href="#about" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2 px-3 py-2 rounded-lg text-zinc-400 text-sm">
              <Info className="w-4 h-4" /> About
            </a>
          </div>
        )}
      </header>

      <main className="flex-1 relative z-10 pt-14">

        {/* ── Hero ── */}
        <section className="min-h-[92vh] flex items-center justify-center px-4 sm:px-6 relative overflow-hidden">
          <div className="max-w-3xl mx-auto text-center">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/[0.12] bg-white/[0.04] text-[11px] font-mono tracking-[0.14em] text-zinc-400 mb-10 uppercase">
              <span className="w-1.5 h-1.5 rounded-full bg-white/70" />
              Astronomical Generative Intelligence Platform
            </div>

            {/* Title */}
            <h1 className="font-display font-black tracking-tight mb-6 leading-none">
              <span className="block text-[clamp(3.5rem,14vw,8rem)] text-white glow-text">ASTRO</span>
              <span className="block text-[clamp(3.5rem,14vw,8rem)] title-gradient">GEN</span>
            </h1>

            {/* Subtitle */}
            <p className="text-base sm:text-lg text-zinc-400 mb-10 max-w-2xl mx-auto leading-relaxed font-light">
              A research-driven platform for astronomical image generation, analysis, and interpretation.
              Multiple deep-learning architectures trained on NASA APOD archives and curated celestial datasets.
            </p>

            {/* CTA buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link href="/generate">
                <Button
                  size="lg"
                  className="h-12 px-7 text-sm font-semibold bg-white text-black hover:bg-zinc-100 rounded-full font-display group transition-all"
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  Begin Session
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-0.5 transition-transform" />
                </Button>
              </Link>
              <a href="#architecture">
                <Button
                  size="lg"
                  variant="outline"
                  className="h-12 px-7 text-sm font-semibold bg-transparent border-white/15 hover:bg-white/[0.06] hover:border-white/25 text-zinc-300 rounded-full font-display transition-all"
                >
                  <GitFork className="w-4 h-4 mr-2" />
                  Explore Architecture
                </Button>
              </a>
            </div>
          </div>
        </section>

        {/* ── Stats ── */}
        <section className="py-12 sm:py-16 relative z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] backdrop-blur-md p-8 sm:p-12">
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-x-4 gap-y-6 sm:gap-4 md:gap-6">
                {STATS.map((s, i) => (
                  <StatItem key={i} target={s.target} suffix={s.suffix} label={s.label} />
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── From raw imagery to interactive intelligence ── */}
        <section id="features" className="py-20 sm:py-28 relative z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="mb-14 max-w-2xl">
              <p className="text-[11px] font-mono tracking-[0.18em] text-zinc-500 uppercase mb-4">Platform capabilities</p>
              <h2 className="font-display text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-5 leading-tight">
                From raw imagery to<br />
                <span className="title-gradient">interactive intelligence</span>
              </h2>
              <p className="text-zinc-400 text-base leading-relaxed">
                Everything you need to explore, generate, and understand the cosmos — powered by state-of-the-art deep learning architectures.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {CAPABILITIES.map((cap, i) => (
                <div
                  key={i}
                  className="group relative rounded-xl border border-white/[0.07] bg-white/[0.03] hover:bg-white/[0.055] hover:border-white/[0.12] p-6 transition-all duration-300 cursor-default"
                >
                  <div className="flex items-start justify-between mb-5">
                    <div className="w-10 h-10 rounded-lg bg-white/[0.07] flex items-center justify-center">
                      <cap.icon className="w-5 h-5 text-white/80" />
                    </div>
                    <span className="text-[10px] font-mono text-zinc-500 bg-white/[0.05] border border-white/[0.08] px-2 py-0.5 rounded-full uppercase tracking-wider">
                      {cap.tag}
                    </span>
                  </div>
                  <h3 className="font-display text-base font-semibold text-white mb-2">{cap.title}</h3>
                  <p className="text-sm text-zinc-500 leading-relaxed">{cap.desc}</p>
                  <div className="mt-4 flex items-center gap-1 text-xs text-zinc-600 group-hover:text-zinc-400 transition-colors">
                    <span>Learn more</span>
                    <ChevronRight className="w-3 h-3" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Architecture Pipeline ── */}
        <section id="architecture" className="py-20 sm:py-28 border-t border-white/[0.05] relative z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-16">
              <p className="text-[11px] font-mono tracking-[0.18em] text-zinc-500 uppercase mb-4">Research pipeline</p>
              <h2 className="font-display text-3xl sm:text-4xl font-bold text-white mb-4">End-to-End Architecture</h2>
              <p className="text-zinc-500 max-w-xl mx-auto text-sm leading-relaxed">
                A unified pipeline from raw astronomical archives to interactive generative intelligence.
              </p>
            </div>

            {/* Horizontal scroll on mobile, row on desktop */}
            <div className="flex flex-row items-start gap-0 overflow-x-auto pb-4 md:pb-0 -mx-4 px-4 md:mx-0 md:px-0 md:justify-between scrollbar-hide">
              {PIPELINE.map((step, i) => (
                <div key={i} className="flex flex-row items-center shrink-0 md:flex-1">
                  {/* Step card */}
                  <div className="flex flex-col items-center w-28 md:w-auto md:flex-1 md:items-center gap-3">
                    <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl border border-white/[0.08] bg-white/[0.04] hover:bg-white/[0.08] flex items-center justify-center group transition-all duration-300 hover:border-white/[0.16] hover:-translate-y-1 shrink-0">
                      <step.icon className="w-6 h-6 md:w-7 md:h-7 text-zinc-400 group-hover:text-white transition-colors" />
                    </div>
                    <div className="text-center">
                      <p className="font-display text-xs md:text-sm font-semibold text-white leading-tight">{step.title}</p>
                      <p className="text-[10px] text-zinc-600 font-mono mt-0.5">{step.desc}</p>
                    </div>
                  </div>
                  {/* Connector */}
                  {i < PIPELINE.length - 1 && (
                    <div className="flex items-center pb-7 mx-1 md:mx-0 shrink-0">
                      <div className="w-6 md:w-10 border-t border-dashed border-white/[0.12]" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Research Innovations ── */}
        <section className="py-20 sm:py-28 border-t border-white/[0.05] relative z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="text-center mb-16">
              <p className="text-[11px] font-mono tracking-[0.18em] text-zinc-500 uppercase mb-4">Under the hood</p>
              <h2 className="font-display text-3xl sm:text-4xl font-bold text-white mb-4">Research Innovations</h2>
              <p className="text-zinc-500 max-w-xl mx-auto text-sm leading-relaxed">
                Cutting-edge techniques developed specifically for astronomical imagery generation and analysis.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {[
                {
                  icon: Brain,
                  title: "Semantic Prompt Conditioning",
                  desc: "LoRA adapters fine-tuned on astronomical vocabulary — galaxy morphology, stellar classification, nebular physics — for precise scene control.",
                  items: null,
                },
                {
                  icon: Zap,
                  title: "Multi-Resolution Consistency",
                  desc: "VAE-GAN refinement ensures structural coherence across scales, from planetary surfaces to galactic filament networks.",
                  items: null,
                },
                {
                  icon: Activity,
                  title: "Perceptual Astronomy Loss",
                  desc: "Custom training objective combining multiple perceptual signals:",
                  items: ["VGG Feature Extraction", "Sobel Edge Detection", "Frequency Domain Analysis", "SSIM & LPIPS Scoring"],
                },
              ].map((card, i) => (
                <div key={i} className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-7 hover:border-white/[0.12] hover:bg-white/[0.05] transition-all duration-300">
                  <div className="w-9 h-9 rounded-lg bg-white/[0.06] flex items-center justify-center mb-5">
                    <card.icon className="w-4.5 h-4.5 text-zinc-300" />
                  </div>
                  <h3 className="font-display text-base font-semibold text-white mb-3">{card.title}</h3>
                  <p className="text-sm text-zinc-500 leading-relaxed mb-4">{card.desc}</p>
                  {card.items && (
                    <ul className="space-y-1.5">
                      {card.items.map((item, j) => (
                        <li key={j} className="flex items-center gap-2 text-xs text-zinc-600 font-mono">
                          <span className="w-1 h-1 rounded-full bg-zinc-600" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── CTA Banner ── */}
        <section id="about" className="py-20 relative z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-10 sm:p-16 text-center">
              <PlanetLogo className="w-10 h-10 text-white/70 mx-auto mb-6" />
              <h2 className="font-display text-3xl sm:text-4xl font-bold text-white mb-4">
                Start exploring the cosmos
              </h2>
              <p className="text-zinc-500 mb-8 max-w-lg mx-auto text-sm leading-relaxed">
                Launch the workspace to generate your first astronomical image, analyze telescope data, or chat with the astrophysics AI.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <Link href="/generate">
                  <Button size="lg" className="h-12 px-8 bg-white text-black hover:bg-zinc-100 rounded-full font-display font-semibold text-sm">
                    <Sparkles className="w-4 h-4 mr-2" />
                    Open Workspace
                  </Button>
                </Link>
                <Link href="/gallery">
                  <Button size="lg" variant="outline" className="h-12 px-8 bg-transparent border-white/15 hover:bg-white/[0.06] text-zinc-300 rounded-full font-display font-semibold text-sm">
                    <ImageIcon className="w-4 h-4 mr-2" />
                    View Gallery
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-white/[0.06] bg-black/50 backdrop-blur-md relative z-10 py-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2 text-white/60">
            <PlanetLogo className="w-4 h-4" />
            <span className="font-display text-sm font-medium tracking-wider">ASTROGEN</span>
            <span className="text-xs text-zinc-700 ml-1">v1.0.0</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 text-[11px] font-mono">
            {[
              { label: "LoRA-SD", key: "lora_sd" as const },
              { label: "VAE-GAN", key: "vae_gan" as const },
              { label: "BLIP-2", key: "blip2" as const },
              { label: "Gemini", key: "gemini" as const },
            ].map(({ label, key }) => (
              <div key={key} className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${
                  status?.models?.[key] || (key === "gemini" && status?.gemini)
                    ? "bg-emerald-500"
                    : "bg-zinc-700"
                }`} />
                <span className="text-zinc-600">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </footer>

      {/* ── Overlays ── */}
      {showKaggle && (
        <KagglePopup onClose={() => setShowKaggle(false)} />
      )}
      {showProfile && (
        <ProfilePanel
          onClose={() => setShowProfile(false)}
          onOpenKagglePopup={() => { setShowProfile(false); setShowKaggle(true); }}
        />
      )}
    </div>
  );
}
