interface GridRendererProps {
  grid: number[][];
  cellSize?: number;
}

const COLOR_MAP: Record<number, string> = {
  0: "#000000", // black
  1: "#1E3A8A", // blue
  2: "#DC2626", // red
  3: "#16A34A", // green
  4: "#EAB308", // yellow
  5: "#6B7280", // gray
  6: "#C026D3", // magenta
  7: "#EA580C", // orange
  8: "#06B6D4", // cyan
  9: "#7F1D1D", // maroon
};

export default function GridRenderer({
  grid,
  cellSize = 24,
}: GridRendererProps) {
  if (!grid || grid.length === 0) {
    return (
      <div className="text-gray-500 text-sm italic">No grid data</div>
    );
  }

  return (
    <div className="inline-block border border-gray-700 rounded overflow-hidden">
      <table
        className="border-collapse"
        style={{ borderSpacing: 0 }}
      >
        <tbody>
          {grid.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  style={{
                    width: cellSize,
                    height: cellSize,
                    minWidth: cellSize,
                    minHeight: cellSize,
                    backgroundColor: COLOR_MAP[cell] ?? "#000000",
                    border: "1px solid rgba(55, 65, 81, 0.5)",
                  }}
                  title={`[${ri},${ci}] = ${cell}`}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="text-xs text-gray-500 px-2 py-1 bg-gray-800/50">
        {grid.length} x {grid[0]?.length ?? 0}
      </div>
    </div>
  );
}
