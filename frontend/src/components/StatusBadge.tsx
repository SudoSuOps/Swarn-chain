interface StatusBadgeProps {
  status: "open" | "solved" | "exhausted" | string;
}

const STATUS_STYLES: Record<string, string> = {
  open: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  solved: "bg-green-500/20 text-green-400 border-green-500/30",
  exhausted: "bg-amber-500/20 text-amber-400 border-amber-500/30",
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const style =
    STATUS_STYLES[status] ??
    "bg-gray-500/20 text-gray-400 border-gray-500/30";

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${style}`}
    >
      {status === "open" && (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 pulse-dot" />
      )}
      {status === "solved" && (
        <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
      )}
      {status === "exhausted" && (
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
      )}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
