export const SUGGESTION_MIME = "application/x-dashboard-suggestion";
export const MOVE_MIME = "application/x-dashboard-move";

export function isChartDrag(e: React.DragEvent): boolean {
  const types = Array.from(e.dataTransfer.types);
  return types.includes(SUGGESTION_MIME) || types.includes(MOVE_MIME);
}
