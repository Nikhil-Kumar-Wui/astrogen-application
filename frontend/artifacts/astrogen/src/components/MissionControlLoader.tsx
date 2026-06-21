import { useEffect, useState } from "react";
import { Progress } from "@/components/ui/progress";
import { Loader2 } from "lucide-react";

const MESSAGES = [
  "Establishing uplink to compute cluster...",
  "Initializing LoRA weights...",
  "Scanning the cosmos...",
  "Mapping star systems...",
  "Analyzing celestial patterns...",
  "Rendering deep-space imagery...",
  "Applying VAE-GAN enhancements...",
  "Finalizing perceptual structures...",
];

export function MissionControlLoader() {
  const [messageIndex, setMessageIndex] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Cycle messages every 2.5 seconds
    const messageInterval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % MESSAGES.length);
    }, 2500);

    // Simulate progress over roughly 15-20 seconds
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) return prev; // Hold at 95% until actually done
        return prev + (Math.random() * 5 + 1);
      });
    }, 1000);

    return () => {
      clearInterval(messageInterval);
      clearInterval(progressInterval);
    };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center p-12 glass-panel rounded-2xl max-w-md mx-auto relative overflow-hidden">
      {/* Subtle pulsing background effect */}
      <div className="absolute inset-0 bg-primary/5 animate-pulse-slow pointer-events-none" />
      
      <div className="relative z-10 flex flex-col items-center text-center">
        <div className="relative mb-6">
          <div className="absolute inset-0 rounded-full bg-primary/20 blur-xl animate-pulse" />
          <Loader2 className="w-12 h-12 text-primary animate-spin" />
        </div>
        
        <h3 className="font-display font-bold text-xl text-foreground mb-2">
          Mission Control is Processing
        </h3>
        
        <p className="text-muted-foreground text-sm h-6 mb-6 transition-opacity duration-300">
          {MESSAGES[messageIndex]}
        </p>

        <div className="w-full space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground font-mono">
            <span>SYS.OP.PROG</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-1" />
        </div>
      </div>
    </div>
  );
}
