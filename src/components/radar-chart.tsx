"use client";

interface DataPoint {
  dimension: string;
  score: number;
  confidence: number;
}

export function RadarChart({ data }: { data: DataPoint[] }) {
  const size = 280;
  const center = size / 2;
  const radius = 110;
  const levels = 5;
  const angleSlice = (Math.PI * 2) / data.length;

  // Generate grid levels
  const gridLevels = Array.from({ length: levels }, (_, i) => {
    const r = (radius / levels) * (i + 1);
    const points = data
      .map((_, j) => {
        const angle = angleSlice * j - Math.PI / 2;
        return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
      })
      .join(" ");
    return points;
  });

  // Data polygon
  const dataPoints = data
    .map((d, i) => {
      const angle = angleSlice * i - Math.PI / 2;
      const r = (d.score / 10) * radius;
      return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
    })
    .join(" ");

  // Label positions
  const labels = data.map((d, i) => {
    const angle = angleSlice * i - Math.PI / 2;
    const labelRadius = radius + 24;
    return {
      x: center + labelRadius * Math.cos(angle),
      y: center + labelRadius * Math.sin(angle),
      label: d.dimension,
      score: d.score,
    };
  });

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[320px]">
      {/* Grid */}
      {gridLevels.map((points, i) => (
        <polygon
          key={i}
          points={points}
          fill="none"
          stroke="var(--border)"
          strokeWidth={0.5}
          opacity={0.5}
        />
      ))}

      {/* Axis lines */}
      {data.map((_, i) => {
        const angle = angleSlice * i - Math.PI / 2;
        return (
          <line
            key={i}
            x1={center}
            y1={center}
            x2={center + radius * Math.cos(angle)}
            y2={center + radius * Math.sin(angle)}
            stroke="var(--border)"
            strokeWidth={0.5}
            opacity={0.3}
          />
        );
      })}

      {/* Data polygon */}
      <polygon
        points={dataPoints}
        fill="var(--primary)"
        fillOpacity={0.15}
        stroke="var(--primary)"
        strokeWidth={1.5}
      />

      {/* Data points */}
      {data.map((d, i) => {
        const angle = angleSlice * i - Math.PI / 2;
        const r = (d.score / 10) * radius;
        return (
          <circle
            key={i}
            cx={center + r * Math.cos(angle)}
            cy={center + r * Math.sin(angle)}
            r={3}
            fill="var(--primary)"
          />
        );
      })}

      {/* Labels */}
      {labels.map((l, i) => (
        <text
          key={i}
          x={l.x}
          y={l.y}
          textAnchor="middle"
          dominantBaseline="central"
          className="fill-muted-foreground text-[9px] font-sans"
        >
          {l.label}
        </text>
      ))}
    </svg>
  );
}
