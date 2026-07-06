import { useState, useRef, useEffect } from "react";
import { Link } from "wouter";
import {
  useGetSessions,
  useGetSessionMessages,
  useCreateSession,
  useDeleteSession,
  useGenerateImage,
  useSendChat,
  useCaptionImage,
  useGetStatus,
  getGetSessionsQueryKey,
  getGetSessionMessagesQueryKey
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Plus, MessageSquare, Trash2, Send, Image as ImageIcon,
  Upload, Download, Copy, Maximize2, Sparkles, Brain,
  Cpu, MessageCircle, PanelLeftClose, PanelLeftOpen, ArrowLeft, X, User
} from "lucide-react";
import { MissionControlLoader } from "@/components/MissionControlLoader";
import { toast } from "sonner";
import { imageUrl } from "@/lib/image-utils";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ProfilePanel } from "@/components/ProfilePanel";

function PlanetLogo({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none" aria-hidden>
      <circle cx="16" cy="16" r="5.5" fill="currentColor" />
      <ellipse cx="16" cy="16" rx="14" ry="5" stroke="currentColor" strokeWidth="1.6" fill="none" transform="rotate(-22 16 16)" />
    </svg>
  );
}

const MODEL_OPTIONS = [
  { value: "lora_sd", label: "LoRA Stable Diffusion", icon: Sparkles, desc: "Text → astronomical image" },
  { value: "vae_gan", label: "VAE-GAN Generation", icon: Cpu, desc: "Autonomous cosmic structures" },
  { value: "blip2", label: "BLIP-2 Vision", icon: Brain, desc: "Image captioning & analysis" },
  { value: "gemini", label: "Gemini Astronomy", icon: MessageCircle, desc: "Astrophysics chat & reasoning" },
];

const EXAMPLE_PROMPTS = [
  "Black hole near a dying star, accretion disk glowing, ultra-realistic",
  "NASA James Webb Space Telescope view of a vibrant nebula",
  "Close-up of a frozen exoplanet surface with a gas giant rising",
];

export default function GeneratePage() {
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [selectedModel, setSelectedModel] = useState("lora_sd");
  const [showProfile, setShowProfile] = useState(false);
  const [settings, setSettings] = useState<any>(null);
  const [imgError, setImgError] = useState(false);

  // Reset image error state when user picture URL changes
  useEffect(() => {
    setImgError(false);
  }, [settings?.user_picture]);

  // Poll settings to pick up sign-in status dynamically
  useEffect(() => {
    let active = true;
    const fetchSettings = () => {
      fetch("http://localhost:8001/settings")
        .then(r => {
          if (!r.ok) throw new Error();
          return r.json();
        })
        .then(d => {
          if (!active) return;
          setSettings(d);
          setImgError(false);
        })
        .catch(() => {});
    };
    fetchSettings();
    const interval = setInterval(fetchSettings, 4000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);
  const [input, setInput] = useState("");
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [fullscreenImage, setFullscreenImage] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: status } = useGetStatus({ query: { refetchInterval: 8000 } as any });
  const sessionsQuery = useGetSessions();
  const sessions = sessionsQuery.data || [];
  const { data: messages = [] } = useGetSessionMessages(activeSessionId!, {
    query: { enabled: !!activeSessionId } as any
  });

  const createSession = useCreateSession();
  const deleteSession = useDeleteSession();
  const generateImage = useGenerateImage();
  const sendChat = useSendChat();
  const captionImage = useCaptionImage();

  const initialized = useRef(false);

  // Auto-create a brand new session when the workspace is mounted
  useEffect(() => {
    if (sessionsQuery.isSuccess) {
      if (!initialized.current) {
        initialized.current = true;
        handleCreateSession();
      } else if (sessions.length === 0 && !createSession.isPending) {
        handleCreateSession();
      }
    }
  }, [sessions, sessionsQuery.isSuccess]);

  const isGenerating = generateImage.isPending || sendChat.isPending || captionImage.isPending;

  useEffect(() => {
    if (scrollRef.current) {
      const vp = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (vp) vp.scrollTop = vp.scrollHeight;
    }
  }, [messages, isGenerating]);

  useEffect(() => {
    const handleGlobalPaste = (e: ClipboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" && target.getAttribute("type") !== "file") {
        return;
      }

      let imageFound = false;

      const files = e.clipboardData?.files;
      if (files && files.length > 0) {
        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          if (file.type.startsWith("image/")) {
            e.preventDefault();
            imageFound = true;
            const reader = new FileReader();
            reader.onloadend = () => {
              setUploadedImage(reader.result as string);
              if (selectedModel !== "blip2" && selectedModel !== "gemini") {
                setSelectedModel("blip2");
                toast.success("Image pasted - switched to BLIP-2 Vision");
              } else {
                toast.success("Image pasted from clipboard");
              }
            };
            reader.readAsDataURL(file);
            return;
          }
        }
      }

      const items = e.clipboardData?.items;
      if (items && !imageFound) {
        for (let i = 0; i < items.length; i++) {
          if (items[i].type.indexOf("image") !== -1) {
            const file = items[i].getAsFile();
            if (file) {
              e.preventDefault();
              imageFound = true;
              const reader = new FileReader();
              reader.onloadend = () => {
                setUploadedImage(reader.result as string);
                if (selectedModel !== "blip2" && selectedModel !== "gemini") {
                  setSelectedModel("blip2");
                  toast.success("Image pasted - switched to BLIP-2 Vision");
                } else {
                  toast.success("Image pasted from clipboard");
                }
              };
              reader.readAsDataURL(file);
              return;
            }
          }
        }
      }

      // Fallback: Read using navigator.clipboard if nothing found in event (QtWebEngine files helper)
      if (!imageFound && navigator.clipboard && navigator.clipboard.read) {
        navigator.clipboard.read().then((data) => {
          for (const item of data) {
            for (const type of item.types) {
              if (type.startsWith("image/")) {
                imageFound = true;
                item.getType(type).then((blob) => {
                  const reader = new FileReader();
                  reader.onloadend = () => {
                    setUploadedImage(reader.result as string);
                    if (selectedModel !== "blip2" && selectedModel !== "gemini") {
                      setSelectedModel("blip2");
                      toast.success("Image pasted - switched to BLIP-2 Vision");
                    } else {
                      toast.success("Image pasted from clipboard");
                    }
                  };
                  reader.readAsDataURL(blob);
                });
                return;
              }
            }
          }
        }).catch(() => {});
      }
    };

    window.addEventListener("paste", handleGlobalPaste);
    return () => {
      window.removeEventListener("paste", handleGlobalPaste);
    };
  }, [selectedModel]);

  const handleCreateSession = (prompt?: string) => {
    createSession.mutate(
      { params: { title: prompt ? prompt.substring(0, 32) + "…" : "New Session" } },
      {
        onSuccess: (data) => {
          queryClient.invalidateQueries({ queryKey: getGetSessionsQueryKey() });
          setActiveSessionId(data.session_id);
          if (prompt) setInput(prompt);
          if (window.innerWidth < 768) setSidebarOpen(false);
        }
      }
    );
  };

  const handleDeleteSession = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteSession.mutate({ sessionId: id }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetSessionsQueryKey() });
        if (activeSessionId === id) setActiveSessionId(null);
      }
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => setUploadedImage(reader.result as string);
    reader.readAsDataURL(file);
  };

  const handleSubmit = () => {
    if (!activeSessionId) return;
    const currentInput = input;
    if (!currentInput.trim() && !uploadedImage && selectedModel !== "vae_gan") return;

    // Clear input immediately so it disappears from the text box
    setInput("");

    const commonOptions = {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetSessionMessagesQueryKey(activeSessionId) });
        setUploadedImage(null);
      },
      onError: (err: Error) => {
        setInput(currentInput);
        toast.error(err.message || "An error occurred");
      }
    };

    if (selectedModel === "lora_sd" || selectedModel === "vae_gan") {
      toast("Generation initiated…");
      generateImage.mutate({ data: { prompt: currentInput, model: selectedModel, session_id: activeSessionId } }, commonOptions);
      // Invalidate queries shortly after mutation starts so the user message appears immediately
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: getGetSessionMessagesQueryKey(activeSessionId) });
      }, 150);
    } else if (selectedModel === "blip2") {
      if (!uploadedImage) { toast.error("Upload an image for BLIP-2 to analyze"); setInput(currentInput); return; }
      captionImage.mutate({ data: { image_b64: uploadedImage.split(",")[1], question: currentInput, session_id: activeSessionId } }, commonOptions);
    } else if (selectedModel === "gemini") {
      sendChat.mutate({ data: { message: currentInput, session_id: activeSessionId, image_b64: uploadedImage ? uploadedImage.split(",")[1] : undefined } }, commonOptions);
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: getGetSessionMessagesQueryKey(activeSessionId) });
      }, 150);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const downloadImage = async (path: string) => {
    try {
      const url = imageUrl(path);
      if (!url) return;
      const blob = await (await fetch(url)).blob();
      const a = Object.assign(document.createElement("a"), {
        href: window.URL.createObjectURL(blob),
        download: `astrogen-${Date.now()}.png`
      });
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(a.href);
      toast.success("Image downloaded");
    } catch {
      toast.error("Failed to download image");
    }
  };

  const needsImageUpload = selectedModel === "blip2" || selectedModel === "gemini";
  const activeSession = sessions.find(s => s.id === activeSessionId);
  const currentModel = MODEL_OPTIONS.find(m => m.value === selectedModel);

  return (
    <div className="h-screen w-full flex bg-background overflow-hidden">
      {/* ── Sidebar overlay on mobile ── */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/60 z-20"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Sidebar ── */}
      <aside
        className={`
          fixed md:relative inset-y-0 left-0 z-30 md:z-auto
          flex flex-col w-72 border-r border-white/[0.06] bg-sidebar
          transition-transform duration-300
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
          ${!sidebarOpen ? "md:hidden" : ""}
        `}
        style={sidebarOpen ? undefined : { width: 0 }}
      >
        {/* Logo */}
        <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-white hover:text-zinc-300 transition-colors">
            <PlanetLogo className="w-5 h-5" />
            <span className="font-display font-bold text-sm tracking-wider">
              ASTRO<span className="title-gradient">GEN</span>
            </span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="md:hidden p-1 text-zinc-600 hover:text-zinc-400"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>

        {/* New Session */}
        <div className="p-3 border-b border-white/[0.06]">
          <Button
            className="w-full justify-start bg-white text-black hover:bg-zinc-100 font-semibold text-sm h-9"
            onClick={() => handleCreateSession()}
          >
            <Plus className="w-4 h-4 mr-2" />
            New Session
          </Button>
        </div>

        {/* Session list */}
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-0.5">
            {sessions.length === 0 && (
              <p className="text-xs text-zinc-700 text-center py-8 px-4 font-mono">No sessions yet</p>
            )}
            {sessions.map(session => (
              <div
                key={session.id}
                onClick={() => { setActiveSessionId(session.id); if (window.innerWidth < 768) setSidebarOpen(false); }}
                className={`w-full flex items-center justify-between p-2.5 rounded-lg text-sm cursor-pointer group transition-all
                  ${activeSessionId === session.id
                    ? "bg-white/[0.08] text-white"
                    : "text-zinc-500 hover:bg-white/[0.04] hover:text-zinc-300"
                  }`}
              >
                <div className="flex items-center gap-2.5 overflow-hidden min-w-0">
                  <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-60" />
                  <span className="truncate text-xs">{session.title}</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 opacity-0 group-hover:opacity-100 text-zinc-700 hover:text-zinc-400 shrink-0 transition-opacity"
                  onClick={(e) => handleDeleteSession(session.id, e)}
                >
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            ))}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="p-3 border-t border-white/[0.06] space-y-2">
          <div className="flex items-center gap-2 text-[11px] font-mono px-1">
            <span className={`w-1.5 h-1.5 rounded-full ${status ? "bg-emerald-500" : "bg-zinc-700 animate-pulse"}`} />
            <span className="text-zinc-600">SYSTEM {status ? "ONLINE" : "OFFLINE"}</span>
          </div>
          <Link href="/gallery">
            <Button variant="outline" className="w-full bg-transparent border-white/[0.08] hover:bg-white/[0.05] text-zinc-500 hover:text-zinc-300 text-xs h-8">
              <ImageIcon className="w-3.5 h-3.5 mr-2" />
              Image Gallery
            </Button>
          </Link>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top bar */}
        <div className="h-12 border-b border-white/[0.06] flex items-center px-4 gap-3 bg-black/40 backdrop-blur-sm shrink-0">
          <button
            onClick={() => setSidebarOpen(v => !v)}
            className="p-1.5 text-zinc-600 hover:text-zinc-300 transition-colors rounded-md hover:bg-white/[0.05]"
          >
            {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
          </button>

          {activeSession ? (
            <h2 className="font-display text-sm font-medium text-zinc-300 truncate">{activeSession.title}</h2>
          ) : (
            <span className="text-sm text-zinc-700 font-mono">Select or create a session</span>
          )}

          <div className="ml-auto flex items-center gap-2">
            {currentModel && (
              <span className="hidden sm:flex items-center gap-1.5 text-[11px] font-mono text-zinc-600 border border-white/[0.06] bg-white/[0.03] px-2 py-0.5 rounded-full">
                <currentModel.icon className="w-3 h-3" />
                {currentModel.label}
              </span>
            )}
            <Link href="/">
              <button className="p-1.5 text-zinc-700 hover:text-zinc-400 transition-colors rounded-md hover:bg-white/[0.05]" title="Go Back">
                <ArrowLeft className="w-4 h-4" />
              </button>
            </Link>
            {/* Profile button */}
            <button
              onClick={() => setShowProfile(v => !v)}
              className="w-7 h-7 rounded-full flex items-center justify-center transition-all overflow-hidden border border-white/10 hover:border-white/20 hover:scale-105"
              style={{
                background: "#18181b",
                boxShadow: showProfile ? "0 0 10px rgba(255,255,255,0.2)" : "none"
              }}
              aria-label="Profile"
            >
              {settings?.user_picture && !imgError ? (
                <img 
                  src={settings.user_picture} 
                  alt="Profile" 
                  className="w-full h-full object-cover" 
                  onError={() => setImgError(true)}
                />
              ) : (
                <User size={13} color="#fff" />
              )}
            </button>
          </div>
        </div>

        {activeSession ? (
          <>
            {/* Messages */}
            <ScrollArea className="flex-1 min-h-0 p-4 sm:p-6" ref={scrollRef}>
              <div className="max-w-3xl mx-auto space-y-6 pb-6">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center max-w-xl mx-auto">
                    <PlanetLogo className="w-12 h-12 text-zinc-700 mb-6" />
                    <h2 className="font-display text-2xl font-bold text-white mb-3">Cosmic Research Station</h2>
                    <p className="text-zinc-500 text-sm mb-10 max-w-sm mx-auto leading-relaxed">
                      This is a new research session. Select a recommended prompt or describe a custom cosmic scene below.
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left w-full">
                      {EXAMPLE_PROMPTS.map((prompt, i) => (
                        <button
                          key={i}
                          onClick={() => setInput(prompt)}
                          className="glass-panel p-5 rounded-xl text-left group hover:border-white/[0.15] hover:bg-white/[0.06] transition-all duration-300"
                        >
                          <Sparkles className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 mb-3 transition-colors" />
                          <p className="text-xs text-zinc-500 group-hover:text-zinc-400 leading-relaxed font-mono transition-colors font-light">
                            "{prompt}"
                          </p>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-[90%] sm:max-w-[80%] rounded-2xl p-4 ${
                        msg.role === "user"
                          ? "bg-white/[0.07] border border-white/[0.08] rounded-tr-sm"
                          : "bg-white/[0.04] border border-white/[0.06] rounded-tl-sm"
                      }`}>
                        {msg.role === "user" && (
                          <div className="flex items-center gap-1.5 mb-3 pb-2 border-b border-white/[0.06] text-[10px] font-mono text-zinc-500 justify-end">
                            <span>{settings?.user_name ? settings.user_name.split(" ")[0].toUpperCase() : "YOU"}</span>
                            <User className="w-2.5 h-2.5" />
                          </div>
                        )}

                        {msg.role === "assistant" && msg.model_used && (
                          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/[0.06] text-[11px] font-mono text-zinc-600">
                            <Brain className="w-3 h-3" />
                            <span>{msg.model_used.toUpperCase()}</span>
                          </div>
                        )}

                        {msg.msg_type === "image" && msg.content ? (
                          <div className="space-y-3 animate-in fade-in zoom-in-95 duration-400">
                            <div className="relative group rounded-xl overflow-hidden border border-white/[0.08]">
                              <img
                                src={imageUrl(msg.content) || ""}
                                alt={msg.prompt || "Generated astronomical image"}
                                className="w-full h-auto object-cover max-h-[480px]"
                              />
                              <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3 backdrop-blur-sm">
                                <Button size="icon" variant="secondary" className="bg-white/10 hover:bg-white/20 border-0" onClick={() => downloadImage(msg.content)}>
                                  <Download className="w-4 h-4" />
                                </Button>
                                <Button size="icon" variant="secondary" className="bg-white/10 hover:bg-white/20 border-0" onClick={() => setFullscreenImage(imageUrl(msg.content))}>
                                  <Maximize2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                            {msg.prompt && (
                              <div className="space-y-2">
                                <p className="text-xs text-zinc-500 italic font-mono border-l-2 border-white/20 pl-3">
                                  "{msg.prompt}"
                                </p>
                                <div className="flex gap-2 flex-wrap">
                                  <Button variant="ghost" size="sm" className="h-7 text-xs text-zinc-600 hover:text-zinc-300 px-2" onClick={() => { navigator.clipboard.writeText(msg.prompt!); toast.success("Copied"); }}>
                                    <Copy className="w-3 h-3 mr-1.5" /> Copy Prompt
                                  </Button>
                                  <Button variant="ghost" size="sm" className="h-7 text-xs text-zinc-600 hover:text-zinc-300 px-2" onClick={() => { setInput(msg.prompt!); setSelectedModel("lora_sd"); }}>
                                    <Sparkles className="w-3 h-3 mr-1.5" /> Regenerate
                                  </Button>
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="text-sm text-zinc-300 leading-relaxed space-y-1">
                            {msg.content.split("\n").map((line, j) => (
                              <p key={j}>{line}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}

                {isGenerating && (
                  <div className="flex justify-center py-8">
                    <MissionControlLoader />
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Input */}
            <div className="p-3 sm:p-5 border-t border-white/[0.06] bg-black/30 backdrop-blur-md shrink-0">
              <div className="max-w-3xl mx-auto space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Select value={selectedModel} onValueChange={setSelectedModel}>
                    <SelectTrigger className="w-auto min-w-[180px] bg-white/[0.04] border-white/[0.08] font-mono text-xs h-8 text-zinc-400">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MODEL_OPTIONS.map(opt => (
                        <SelectItem key={opt.value} value={opt.value} className="text-sm">
                          <div className="flex items-center gap-2">
                            <opt.icon className="w-3.5 h-3.5 text-zinc-400" />
                            <span>{opt.label}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  {needsImageUpload && (
                    <>
                      <input type="file" accept="image/*" className="hidden" ref={fileInputRef} onChange={handleFileUpload} />
                      <Button
                        variant="outline"
                        size="sm"
                        className={`h-8 text-xs border-white/[0.08] ${uploadedImage ? "bg-white/[0.08] text-zinc-300 border-white/[0.15]" : "bg-transparent text-zinc-600 hover:text-zinc-300"}`}
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <Upload className="w-3.5 h-3.5 mr-1.5" />
                        {uploadedImage ? "Image Attached" : "Attach Image"}
                      </Button>
                      {uploadedImage && (
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-zinc-700 hover:text-destructive" onClick={() => setUploadedImage(null)}>
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      )}
                    </>
                  )}
                </div>
                {uploadedImage && (
                  <div className="relative inline-flex items-center gap-2 p-1 bg-white/[0.03] border border-white/[0.08] rounded-xl w-fit group">
                    <div className="relative h-16 w-16 rounded-lg overflow-hidden border border-white/[0.06]">
                      <img
                        src={uploadedImage}
                        alt="Clipboard preview"
                        className="h-full w-full object-cover"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => setUploadedImage(null)}
                      className="absolute -top-2 -right-2 bg-zinc-950 hover:bg-red-950 text-zinc-400 hover:text-red-400 border border-white/[0.1] rounded-full p-1 transition-all shadow-lg cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}

                <div className="relative">
                  <Textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onPaste={(e) => {
                      const files = e.clipboardData.files;
                      if (files && files.length > 0) {
                        const file = files[0];
                        if (file.type.startsWith("image/")) {
                          e.preventDefault();
                          const reader = new FileReader();
                          reader.onloadend = () => {
                            setUploadedImage(reader.result as string);
                            if (selectedModel !== "blip2" && selectedModel !== "gemini") {
                              setSelectedModel("blip2");
                              toast.success("Image pasted - switched to BLIP-2 Vision");
                            } else {
                              toast.success("Image pasted from clipboard");
                            }
                          };
                          reader.readAsDataURL(file);
                          return;
                        }
                      }

                      const items = e.clipboardData.items;
                      for (let i = 0; i < items.length; i++) {
                        if (items[i].type.indexOf("image") !== -1) {
                          const file = items[i].getAsFile();
                          if (file) {
                            e.preventDefault();
                            const reader = new FileReader();
                            reader.onloadend = () => {
                              setUploadedImage(reader.result as string);
                              if (selectedModel !== "blip2" && selectedModel !== "gemini") {
                                setSelectedModel("blip2");
                                toast.success("Image pasted - switched to BLIP-2 Vision");
                              } else {
                                toast.success("Image pasted from clipboard");
                              }
                            };
                            reader.readAsDataURL(file);
                            break;
                          }
                        }
                      }
                    }}
                    placeholder={
                      selectedModel === "vae_gan" ? "VAE-GAN will generate structures autonomously (prompt optional)…" :
                      selectedModel === "blip2" ? "Ask a question about the uploaded image… (Enter to send)" :
                      "Describe the astronomical scene to generate… (Enter to send, Shift+Enter for new line)"
                    }
                    className="min-h-[72px] bg-white/[0.03] border-white/[0.08] focus-visible:ring-white/20 focus-visible:border-white/20 pr-14 resize-none text-sm placeholder:text-zinc-700"
                    disabled={isGenerating}
                  />
                  <Button
                    size="icon"
                    className="absolute bottom-3 right-3 h-9 w-9 bg-white text-black hover:bg-zinc-200 rounded-lg"
                    onClick={handleSubmit}
                    disabled={isGenerating || (!input.trim() && !uploadedImage && selectedModel !== "vae_gan")}
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
                <p className="text-[10px] text-zinc-800 text-center font-mono">Enter to send · Shift+Enter for new line</p>
              </div>
            </div>
          </>
        ) : (
          /* Empty state */
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="max-w-xl w-full text-center">
              <PlanetLogo className="w-12 h-12 text-zinc-700 mx-auto mb-6" />
              <h2 className="font-display text-3xl font-bold text-white mb-3">Open a Session</h2>
              <p className="text-zinc-500 text-sm mb-10 max-w-sm mx-auto leading-relaxed">
                Create a new research session to start generating and analyzing astronomical imagery.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left">
                {EXAMPLE_PROMPTS.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => handleCreateSession(prompt)}
                    className="glass-panel p-5 rounded-xl text-left group hover:border-white/[0.15] hover:bg-white/[0.06] transition-all duration-300"
                  >
                    <Sparkles className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 mb-3 transition-colors" />
                    <p className="text-xs text-zinc-500 group-hover:text-zinc-400 leading-relaxed font-mono transition-colors">
                      "{prompt}"
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <Dialog open={!!fullscreenImage} onOpenChange={(open) => !open && setFullscreenImage(null)}>
        <DialogContent className="max-w-[92vw] max-h-[92vh] p-1 bg-black/95 border-white/[0.08]">
          {fullscreenImage && (
            <img src={fullscreenImage} alt="Fullscreen preview" className="w-full h-full object-contain rounded-lg" />
          )}
        </DialogContent>
      </Dialog>

      {showProfile && (
        <ProfilePanel onClose={() => setShowProfile(false)} />
      )}
    </div>
  );
}
