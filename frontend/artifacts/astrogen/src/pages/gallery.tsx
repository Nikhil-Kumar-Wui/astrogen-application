import { Link } from "wouter";
import { useGetGallery } from "@workspace/api-client-react";
import { imageUrl } from "@/lib/image-utils";
import { Starfield } from "@/components/Starfield";
import { Download, Sparkles, ArrowLeft, Grid3X3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { toast } from "sonner";

function PlanetLogo({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none" aria-hidden>
      <circle cx="16" cy="16" r="5.5" fill="currentColor" />
      <ellipse cx="16" cy="16" rx="14" ry="5" stroke="currentColor" strokeWidth="1.6" fill="none" transform="rotate(-22 16 16)" />
    </svg>
  );
}

export default function GalleryPage() {
  const { data: images = [], isLoading } = useGetGallery({ limit: 100 });
  const [fullscreenImage, setFullscreenImage] = useState<{ url: string; prompt?: string; model?: string } | null>(null);

  const downloadImage = async (path: string, e: React.MouseEvent) => {
    e.stopPropagation();
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

  return (
    <div className="min-h-screen bg-background relative">
      <Starfield />

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.06] bg-black/70 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/generate">
              <button className="p-1.5 text-zinc-600 hover:text-zinc-300 transition-colors rounded-md hover:bg-white/[0.05]">
                <ArrowLeft className="w-4 h-4" />
              </button>
            </Link>
            <div className="flex items-center gap-2 border-l border-white/[0.08] pl-3">
              <PlanetLogo className="w-4 h-4 text-zinc-400" />
              <span className="font-display font-semibold text-sm text-white">
                ASTRO<span className="title-gradient">GEN</span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Grid3X3 className="w-4 h-4 text-zinc-600" />
            <span className="text-sm font-display text-zinc-400">Archive</span>
            {images.length > 0 && (
              <span className="text-[11px] font-mono text-zinc-700 border border-white/[0.07] px-2 py-0.5 rounded-full ml-1">
                {images.length}
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="pt-20 pb-20 px-4 sm:px-6 max-w-7xl mx-auto relative z-10">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-40 gap-4">
            <PlanetLogo className="w-10 h-10 text-zinc-700 animate-spin" />
            <p className="text-xs font-mono text-zinc-700 uppercase tracking-widest">Loading archive…</p>
          </div>
        ) : images.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 text-center max-w-sm mx-auto">
            <div className="w-20 h-20 rounded-full border border-white/[0.07] bg-white/[0.03] flex items-center justify-center mb-6">
              <Sparkles className="w-8 h-8 text-zinc-700" />
            </div>
            <h3 className="font-display text-2xl font-bold text-white mb-3">Archive Empty</h3>
            <p className="text-zinc-500 text-sm mb-8 leading-relaxed">
              Generate your first astronomical image in the workspace to start building your archive.
            </p>
            <Link href="/generate">
              <Button className="bg-white text-black hover:bg-zinc-100 rounded-full font-display font-semibold text-sm">
                Open Workspace
              </Button>
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-10">
              <h1 className="font-display text-2xl sm:text-3xl font-bold text-white mb-2">Archive Gallery</h1>
              <p className="text-zinc-500 text-sm">
                {images.length} image{images.length !== 1 ? "s" : ""} generated across all sessions
              </p>
            </div>

            <div className="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 gap-4 space-y-4">
              {images.map((img) => (
                <div
                  key={img.id}
                  className="break-inside-avoid relative group rounded-xl overflow-hidden border border-white/[0.06] bg-white/[0.03] cursor-pointer hover:border-white/[0.12] transition-colors duration-300"
                  onClick={() => setFullscreenImage({ url: imageUrl(img.filepath) || "", prompt: img.prompt || undefined, model: img.model || undefined })}
                >
                  <img
                    src={imageUrl(img.filepath) || ""}
                    alt={img.prompt || "Generated astronomical image"}
                    className="w-full h-auto object-cover transform group-hover:scale-[1.02] transition-transform duration-500 ease-out"
                    loading="lazy"
                  />

                  <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <div className="absolute bottom-0 left-0 right-0 p-4">
                      <div className="flex items-center justify-between mb-2">
                        {img.model && (
                          <span className="text-[10px] font-mono text-white/70 bg-white/[0.08] border border-white/[0.1] px-2 py-0.5 rounded-full uppercase tracking-wider">
                            {img.model}
                          </span>
                        )}
                        <button
                          className="ml-auto p-1.5 rounded-lg bg-white/[0.08] hover:bg-white/[0.16] text-white/70 hover:text-white transition-colors"
                          onClick={(e) => downloadImage(img.filepath, e)}
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      {img.prompt && (
                        <p className="text-[11px] text-white/60 line-clamp-2 leading-snug font-light">
                          {img.prompt}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </main>

      {/* Fullscreen dialog */}
      <Dialog open={!!fullscreenImage} onOpenChange={(open) => !open && setFullscreenImage(null)}>
        <DialogContent className="max-w-[94vw] max-h-[94vh] p-0 bg-black/98 border-white/[0.07] overflow-hidden rounded-2xl">
          {fullscreenImage && (
            <div className="flex flex-col h-full">
              <img
                src={fullscreenImage.url}
                alt="Full preview"
                className="w-full h-auto object-contain max-h-[82vh]"
              />
              {(fullscreenImage.prompt || fullscreenImage.model) && (
                <div className="p-5 border-t border-white/[0.07] flex items-start justify-between gap-4">
                  <div>
                    {fullscreenImage.model && (
                      <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-wider block mb-1">{fullscreenImage.model}</span>
                    )}
                    {fullscreenImage.prompt && (
                      <p className="text-sm text-zinc-400 leading-relaxed">{fullscreenImage.prompt}</p>
                    )}
                  </div>
                  <button
                    className="shrink-0 p-2 rounded-lg border border-white/[0.08] bg-white/[0.04] text-zinc-500 hover:text-zinc-200 hover:border-white/[0.15] transition-all"
                    onClick={() => {
                      const a = document.createElement("a");
                      a.href = fullscreenImage.url;
                      a.download = `astrogen-${Date.now()}.png`;
                      a.click();
                    }}
                  >
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
