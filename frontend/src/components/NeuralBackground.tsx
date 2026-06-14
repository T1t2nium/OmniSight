import { useEffect, useRef } from "react";

interface NeuralBackgroundProps {
  className?: string;
  /**
   * Color of the particles.
   * Defaults to indigo-500 (#6366f1).
   */
  color?: string;
  /**
   * The opacity of the trails (0.0 to 1.0).
   * Lower = longer trails. Higher = shorter trails.
   * Default: 0.12
   */
  trailOpacity?: number;
  /**
   * Number of particles. Default: 600
   */
  particleCount?: number;
  /**
   * Speed multiplier. Default: 1
   */
  speed?: number;
}

/**
 * Full-viewport canvas background that renders a flow-field particle system.
 *
 * Particles follow a position-based angle field (simplex-like noise),
 * creating organic, fluid motion. The mouse repels particles within a
 * 150px radius for subtle interactivity.
 *
 * Adapted for the OmniSight design system — no Tailwind, no shadcn.
 * Trail colour is read from --color-bg-primary CSS variable on :root.
 */
export default function NeuralBackground({
  className,
  color = "#6366f1",
  trailOpacity = 0.12,
  particleCount = 600,
  speed = 1,
}: NeuralBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Check for reduced-motion preference
    const motionQuery = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    );
    if (motionQuery.matches) {
      // Render a single static frame — no animation loop
      let width = container.clientWidth;
      let height = container.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      // Draw scattered static dots
      ctx.fillStyle = color;
      for (let i = 0; i < particleCount; i++) {
        const x = Math.random() * width;
        const y = Math.random() * height;
        ctx.globalAlpha = 0.3 + Math.random() * 0.4;
        ctx.fillRect(x, y, 1.5, 1.5);
      }
      ctx.globalAlpha = 1;
      return;
    }

    // ---- Read background colour from design tokens ----
    const bgHex = getComputedStyle(document.documentElement)
      .getPropertyValue("--color-bg-primary")
      .trim();
    let bgR = 0, bgG = 0, bgB = 0;
    if (bgHex && bgHex.startsWith("#") && bgHex.length >= 7) {
      bgR = parseInt(bgHex.slice(1, 3), 16);
      bgG = parseInt(bgHex.slice(3, 5), 16);
      bgB = parseInt(bgHex.slice(5, 7), 16);
    }
    // Fallback to near-black if token unavailable
    const trailBg = `rgba(${bgR || 15}, ${bgG || 15}, ${bgB || 20}, ${trailOpacity})`;

    // ---- State ----
    let width = container.clientWidth;
    let height = container.clientHeight;
    let particles: Particle[] = [];
    let animationFrameId: number;
    let mouse = { x: -1000, y: -1000 };

    // ---- Particle class ----
    class Particle {
      x: number;
      y: number;
      vx: number;
      vy: number;
      age: number;
      life: number;

      constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = 0;
        this.vy = 0;
        this.age = 0;
        this.life = Math.random() * 200 + 100;
      }

      update() {
        // Flow field: angle based on position (simplex-like)
        const angle =
          (Math.cos(this.x * 0.005) + Math.sin(this.y * 0.005)) * Math.PI;

        // Add force from flow field
        this.vx += Math.cos(angle) * 0.2 * speed;
        this.vy += Math.sin(angle) * 0.2 * speed;

        // Mouse repulsion within interaction radius
        const dx = mouse.x - this.x;
        const dy = mouse.y - this.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const interactionRadius = 150;

        if (distance < interactionRadius && distance > 0) {
          const force = (interactionRadius - distance) / interactionRadius;
          this.vx -= (dx / distance) * force * 0.05;
          this.vy -= (dy / distance) * force * 0.05;
        }

        // Apply velocity + friction
        this.x += this.vx;
        this.y += this.vy;
        this.vx *= 0.95;
        this.vy *= 0.95;

        // Aging
        this.age++;
        if (this.age > this.life) {
          this.reset();
        }

        // Wrap around screen edges
        if (this.x < 0) this.x = width;
        if (this.x > width) this.x = 0;
        if (this.y < 0) this.y = height;
        if (this.y > height) this.y = 0;
      }

      reset() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = 0;
        this.vy = 0;
        this.age = 0;
        this.life = Math.random() * 200 + 100;
      }

      draw(context: CanvasRenderingContext2D) {
        context.fillStyle = color;
        // Fade in and out based on lifecycle position
        const alpha =
          1 - Math.abs(this.age / this.life - 0.5) * 2;
        context.globalAlpha = alpha * 0.9;
        context.fillRect(this.x, this.y, 1.5, 1.5);
      }
    }

    // ---- Initialization ----
    const init = () => {
      width = container.clientWidth;
      height = container.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); // Reset + apply DPR
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      particles = [];
      for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
      }
    };

    // ---- Animation loop ----
    const animate = () => {
      // Trail effect: semi-transparent overlay instead of clear
      ctx.fillStyle = trailBg;
      ctx.fillRect(0, 0, width, height);

      for (const p of particles) {
        p.update();
        p.draw(ctx);
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    // ---- Event handlers ----
    const handleResize = () => {
      width = container.clientWidth;
      height = container.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      // Re-seed particles for the new dimensions
      particles = [];
      for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    };

    const handleMouseLeave = () => {
      mouse.x = -1000;
      mouse.y = -1000;
    };

    // ---- Start ----
    init();
    animate();

    window.addEventListener("resize", handleResize);
    canvas.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mouseleave", handleMouseLeave);

    // Handle reduced-motion preference changes at runtime
    const handleMotionChange = (e: MediaQueryListEvent) => {
      if (e.matches) {
        cancelAnimationFrame(animationFrameId);
        // Draw static frame
        ctx.fillStyle = trailBg;
        ctx.fillRect(0, 0, width, height);
        ctx.fillStyle = color;
        for (let i = 0; i < particleCount; i++) {
          const x = Math.random() * width;
          const y = Math.random() * height;
          ctx.globalAlpha = 0.3 + Math.random() * 0.4;
          ctx.fillRect(x, y, 1.5, 1.5);
        }
        ctx.globalAlpha = 1;
      } else {
        // Restart animation
        init();
        animate();
      }
    };
    motionQuery.addEventListener("change", handleMotionChange);

    return () => {
      window.removeEventListener("resize", handleResize);
      canvas.removeEventListener("mousemove", handleMouseMove);
      canvas.removeEventListener("mouseleave", handleMouseLeave);
      motionQuery.removeEventListener("change", handleMotionChange);
      cancelAnimationFrame(animationFrameId);
    };
  }, [color, trailOpacity, particleCount, speed]);

  const combinedClassName = ["neural-bg", className].filter(Boolean).join(" ");

  return (
    <div
      ref={containerRef}
      className={combinedClassName}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        overflow: "hidden",
        pointerEvents: "none",
      }}
      aria-hidden="true"
    >
      <canvas
        ref={canvasRef}
        style={{
          display: "block",
          width: "100%",
          height: "100%",
          pointerEvents: "auto",
        }}
      />
    </div>
  );
}
