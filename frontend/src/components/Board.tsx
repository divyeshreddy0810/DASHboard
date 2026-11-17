import { useState } from "react";
import { MOVE_MIME, SUGGESTION_MIME, isChartDrag } from "../dnd";
import type { ChartSpec, RenderedChart } from "../types";
import { ChartCard } from "./ChartCard";

interface Props {
  charts: RenderedChart[];
  onAdd: (chart: ChartSpec, index: number) => void;
  onMove: (chartId: string, index: number) => void;
  onRemove: (chartId: string) => void;
}

export function Board({ charts, onAdd, onMove, onRemove }: Props) {
  const [dropIndex, setDropIndex] = useState<number | null>(null);

  const handleDrop = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    setDropIndex(null);
    const suggestion = e.dataTransfer.getData(SUGGESTION_MIME);
    if (suggestion) {
      onAdd(JSON.parse(suggestion) as ChartSpec, index);
      return;
    }
    const moving = e.dataTransfer.getData(MOVE_MIME);
    if (moving) onMove(moving, index);
  };

  const overCard = (e: React.DragEvent<HTMLDivElement>, i: number) => {
    if (!isChartDrag(e)) return;
    e.preventDefault();
    const rect = e.currentTarget.getBoundingClientRect();
    setDropIndex(e.clientX < rect.left + rect.width / 2 ? i : i + 1);
  };

  return (
    <div
      className={`grid${dropIndex !== null ? " dragging" : ""}`}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setDropIndex(null);
      }}
    >
      {charts.map((c, i) => (
        <div
          key={c.spec.id}
          className={`slot w-${c.spec.width}${dropIndex === i ? " drop-before" : ""}${dropIndex === i + 1 && i === charts.length - 1 ? " drop-after" : ""}`}
          onDragOver={(e) => overCard(e, i)}
          onDrop={(e) => handleDrop(e, dropIndex ?? i)}
        >
          <ChartCard
            chart={c}
            onRemove={() => onRemove(c.spec.id)}
            onDragStart={(e) => {
              e.dataTransfer.setData(MOVE_MIME, c.spec.id);
              e.dataTransfer.effectAllowed = "move";
            }}
          />
        </div>
      ))}
      <div
        className="drop-end"
        onDragOver={(e) => {
          if (!isChartDrag(e)) return;
          e.preventDefault();
          setDropIndex(charts.length);
        }}
        onDrop={(e) => handleDrop(e, charts.length)}
      >
        Drop here to add at the end
      </div>
    </div>
  );
}
