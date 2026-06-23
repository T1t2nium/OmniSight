import { useRef, useEffect } from 'react';

export interface RadarScore {
  label: string;
  value: number; // 0-100
}

interface RadarChartProps {
  scores: RadarScore[];
  size?: number;
  color?: string;
}

/**
 * Zero-dependency radar/spider chart using HTML5 Canvas API.
 *
 * Draws a filled polygon over a pentagonal grid with value labels.
 */
export function RadarChart({
  scores,
  size = 220,
  color = '#10b981',
}: RadarChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || scores.length === 0) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.scale(dpr, dpr);

    const cx = size / 2;
    const cy = size / 2;
    const radius = size * 0.35;
    const levels = 5; // Grid lines

    // Draw grid (concentric pentagons)
    for (let lvl = 1; lvl <= levels; lvl++) {
      const r = (radius * lvl) / levels;
      drawPolygon(ctx, cx, cy, scores.length, r, 'rgba(255,255,255,0.12)', 'rgba(255,255,255,0.06)');
    }

    // Draw axes
    for (let i = 0; i < scores.length; i++) {
      const angle = getAngle(i, scores.length);
      const ex = cx + radius * Math.cos(angle);
      const ey = cy + radius * Math.sin(angle);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(ex, ey);
      ctx.strokeStyle = 'rgba(255,255,255,0.1)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw data polygon
    const points = scores.map((s, i) => {
      const angle = getAngle(i, scores.length);
      const r = radius * (Math.max(0, Math.min(s.value, 100)) / 100);
      return {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      };
    });

    // Filled area
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y);
    }
    ctx.closePath();
    ctx.fillStyle = `${color}33`; // ~20% opacity
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw data points
    points.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
    });

    // Draw labels
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    scores.forEach((s, i) => {
      const angle = getAngle(i, scores.length);
      const lx = cx + (radius + 26) * Math.cos(angle);
      const ly = cy + (radius + 26) * Math.sin(angle);
      ctx.fillText(s.label, lx, ly);
    });

    // Draw value in center
    const avg = Math.round(
      scores.reduce((sum, s) => sum + s.value, 0) / scores.length
    );
    ctx.fillStyle = 'rgba(255,255,255,0.9)';
    ctx.font = 'bold 20px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${avg}`, cx, cy - 4);
    ctx.font = '9px sans-serif';
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.fillText('综合', cx, cy + 12);
  }, [scores, size, color]);

  return (
    <canvas
      ref={canvasRef}
      className="radar-chart"
      width={size}
      height={size}
    />
  );
}

/** Calculate angle for the i-th vertex of an n-gon (starting from top). */
function getAngle(i: number, n: number): number {
  return (Math.PI * 2 * i) / n - Math.PI / 2;
}

/** Draw a regular polygon (no fill by default). */
function drawPolygon(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  sides: number,
  radius: number,
  strokeStyle: string,
  fillStyle?: string,
) {
  ctx.beginPath();
  for (let i = 0; i <= sides; i++) {
    const angle = getAngle(i % sides, sides);
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  if (fillStyle) {
    ctx.fillStyle = fillStyle;
    ctx.fill();
  }
  ctx.strokeStyle = strokeStyle;
  ctx.lineWidth = 1;
  ctx.stroke();
}
