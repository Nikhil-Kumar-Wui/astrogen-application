import { useEffect, useRef } from "react";

export function Starfield() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = window.innerWidth;
    let height = window.innerHeight;
    const isMobile = width < 768;

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };
    window.addEventListener("resize", resize);
    resize();

    const numStars = isMobile ? 120 : 220;
    const stars: { x: number; y: number; size: number; speed: number; opacity: number; twinkleSpeed: number }[] = [];

    for (let i = 0; i < numStars; i++) {
      stars.push({
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * 1.4 + 0.3,
        speed: Math.random() * 0.15 + 0.03,
        opacity: Math.random() * 0.8 + 0.2,
        twinkleSpeed: (Math.random() - 0.5) * 0.008,
      });
    }

    type ShootingStar = { x: number; y: number; len: number; speed: number; opacity: number };
    const shootingStars: ShootingStar[] = [];

    const spawnShootingStar = () => {
      if (!isMobile && Math.random() < 0.004 && shootingStars.length < 3) {
        shootingStars.push({
          x: Math.random() * width * 0.8,
          y: Math.random() * height * 0.3,
          len: Math.random() * 100 + 60,
          speed: Math.random() * 8 + 6,
          opacity: 1,
        });
      }
    };

    let frameCount = 0;

    const render = () => {
      frameCount++;
      ctx.clearRect(0, 0, width, height);

      // Very subtle background vignette — neutral, no color tint
      const vignette = ctx.createRadialGradient(width / 2, height / 2, height * 0.1, width / 2, height / 2, height * 0.9);
      vignette.addColorStop(0, "rgba(0,0,0,0)");
      vignette.addColorStop(1, "rgba(0,0,0,0.4)");
      ctx.fillStyle = vignette;
      ctx.fillRect(0, 0, width, height);

      // Stars
      stars.forEach(star => {
        star.y -= star.speed;
        star.opacity += star.twinkleSpeed;
        if (star.opacity > 0.95) { star.opacity = 0.95; star.twinkleSpeed *= -1; }
        if (star.opacity < 0.1) { star.opacity = 0.1; star.twinkleSpeed *= -1; }
        if (star.y < -2) {
          star.y = height + 2;
          star.x = Math.random() * width;
        }
        ctx.globalAlpha = star.opacity;
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Shooting stars
      if (frameCount % 2 === 0) spawnShootingStar();

      for (let i = shootingStars.length - 1; i >= 0; i--) {
        const s = shootingStars[i];
        const gradient = ctx.createLinearGradient(s.x, s.y, s.x - s.len * 0.7, s.y + s.len * 0.7);
        gradient.addColorStop(0, `rgba(255,255,255,${s.opacity})`);
        gradient.addColorStop(1, "rgba(255,255,255,0)");
        ctx.globalAlpha = 1;
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(s.x - s.len * 0.7, s.y + s.len * 0.7);
        ctx.stroke();
        s.x -= s.speed * 0.8;
        s.y += s.speed;
        s.opacity -= 0.018;
        if (s.opacity <= 0) shootingStars.splice(i, 1);
      }

      ctx.globalAlpha = 1;
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0"
      style={{ background: "hsl(0 0% 4%)" }}
    />
  );
}
