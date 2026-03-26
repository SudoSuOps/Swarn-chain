interface ScoreBarProps {
  score: number;
  height?: number;
  showLabel?: boolean;
}

export default function ScoreBar({
  score,
  height = 8,
  showLabel = true,
}: ScoreBarProps) {
  const pct = Math.min(Math.max(score * 100, 0), 100);

  // Color gradient: red (0) -> yellow (0.5) -> green (1.0)
  let barColor = "bg-red-500";
  if (pct >= 80) barColor = "bg-green-500";
  else if (pct >= 60) barColor = "bg-emerald-500";
  else if (pct >= 40) barColor = "bg-yellow-500";
  else if (pct >= 20) barColor = "bg-orange-500";

  return (
    <div className="flex items-center gap-2">
      <div
        className="flex-1 bg-gray-800 rounded-full overflow-hidden"
        style={{ height }}
      >
        <div
          className={`h-full ${barColor} rounded-full transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-mono text-gray-400 min-w-[3rem] text-right">
          {score.toFixed(3)}
        </span>
      )}
    </div>
  );
}
