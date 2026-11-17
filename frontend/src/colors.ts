import { createContext, useContext } from "react";
import type { RenderedChart } from "./types";

// Category name -> palette slot. Shared across a dashboard so "North" is the
// same color in every chart and keeps its color when charts change.
export type SlotMap = Map<string, number>;

export function assignSlots(charts: RenderedChart[], slots: SlotMap): SlotMap {
  const next = new Map(slots);
  const add = (name: string) => {
    if (!next.has(name)) next.set(name, next.size % 8);
  };
  for (const { spec, data } of charts) {
    if (!data) continue;
    if (spec.type === "pie") data.rows?.forEach((r) => add(String(r.x)));
    else if ((data.keys?.length ?? 0) > 1) data.keys!.forEach(add);
  }
  return next;
}

export const SlotContext = createContext<SlotMap>(new Map());

export function useSlot() {
  const slots = useContext(SlotContext);
  return (name: string, fallback: number) => slots.get(name) ?? fallback;
}
