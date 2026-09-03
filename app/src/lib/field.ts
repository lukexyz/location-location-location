import { pinSizeForZoom } from "./pins";

/** A candidate projected onto the map container, in CSS pixels. */
export interface ScreenPin {
  id: string;
  x: number;
  y: number;
  name: string;
  rank: number;
}

/** Which side of its pin a name sits on. */
export type LabelSide = "right" | "left";

/** A point or a size on the map container, in CSS pixels. */
export interface Point { x: number; y: number }
export interface Size { width: number; height: number }

/**
 * What the field draws at one zoom and pan: how wide each pin is, which pins
 * carry their name and on which side, where the selected pin sits (so the card
 * can anchor to it), and how big the field is.
 */
export interface FieldPlan {
  size: number;
  labelled: ReadonlyMap<string, LabelSide>;
  anchor?: Point;
  field?: Size;
}

export const MIN_PIN = 34;
const LABEL_GAP = 6;
const LABEL_HEIGHT = 22;
const LABEL_CHAR = 7;
const LABEL_PAD = 20;
const CLEARANCE = 2;

/**
 * Pin diameter for a field: the zoom's size, shrunk when a quarter of the pins
 * sit closer than that to their nearest neighbour. A three-town demo keeps the
 * big pins; nineteen suburbs inside a ten-minute circle get pins that clear each other.
 */
export function pinSizeForField(zoom: number, pins: readonly { x: number; y: number }[]): number {
  const base = pinSizeForZoom(zoom);
  const nearest = nearestDistances(pins);
  if (nearest.length === 0) return base;
  const crowded = quantile(nearest, 0.25);
  return Math.max(MIN_PIN, Math.min(base, Math.floor(crowded) - CLEARANCE));
}

/**
 * Which pins get a name beside them, and on which side. The selected place is
 * labelled first, then the rest in rank order; each name tries the right of its
 * pin, then the left, and is drawn only where it overlaps no pin and no label
 * already placed, so the best places keep their names in a crowd. The selected
 * place is always named, on the right if nowhere is clear.
 */
export function planLabels(pins: readonly ScreenPin[], size: number, selectedId: string): Map<string, LabelSide> {
  const half = size / 2;
  const pinBoxes = pins.map((pin) => box(pin.x - half, pin.y - half, size, size));
  const order = [...pins].sort((a, b) => (a.id === selectedId ? -1 : b.id === selectedId ? 1 : a.rank - b.rank));
  const placed: Box[] = [];
  const labelled = new Map<string, LabelSide>();
  for (const pin of order) {
    const width = labelWidth(pin.name);
    const top = pin.y - LABEL_HEIGHT / 2;
    const options: [LabelSide, Box][] = [
      ["right", box(pin.x + half + LABEL_GAP, top, width, LABEL_HEIGHT)],
      ["left", box(pin.x - half - LABEL_GAP - width, top, width, LABEL_HEIGHT)],
    ];
    const clear = options.find(([, label]) =>
      !pinBoxes.some((other) => overlaps(label, other)) && !placed.some((other) => overlaps(label, other)));
    const chosen = clear ?? (pin.id === selectedId ? options[0] : undefined);
    if (!chosen) continue;
    placed.push(chosen[1]);
    labelled.set(pin.id, chosen[0]);
  }
  return labelled;
}

export function samePlan(a: FieldPlan, b: FieldPlan): boolean {
  if (a.size !== b.size || a.labelled.size !== b.labelled.size) return false;
  for (const [id, side] of a.labelled) if (b.labelled.get(id) !== side) return false;
  if (!samePoint(a.anchor, b.anchor)) return false;
  return a.field?.width === b.field?.width && a.field?.height === b.field?.height;
}

function samePoint(a: Point | undefined, b: Point | undefined): boolean {
  if (!a || !b) return a === b;
  return Math.round(a.x) === Math.round(b.x) && Math.round(a.y) === Math.round(b.y);
}

interface Box { left: number; top: number; right: number; bottom: number }

function box(left: number, top: number, width: number, height: number): Box {
  return { left, top, right: left + width, bottom: top + height };
}

function overlaps(a: Box, b: Box): boolean {
  return a.left < b.right + CLEARANCE && b.left < a.right + CLEARANCE && a.top < b.bottom + CLEARANCE && b.top < a.bottom + CLEARANCE;
}

function labelWidth(name: string): number {
  return name.length * LABEL_CHAR + LABEL_PAD;
}

function nearestDistances(pins: readonly { x: number; y: number }[]): number[] {
  return pins.map((pin, index) => {
    let nearest = Infinity;
    pins.forEach((other, otherIndex) => {
      if (otherIndex === index) return;
      nearest = Math.min(nearest, Math.hypot(pin.x - other.x, pin.y - other.y));
    });
    return nearest;
  }).filter(Number.isFinite);
}

function quantile(values: readonly number[], fraction: number): number {
  const sorted = [...values].sort((a, b) => a - b);
  const position = Math.min(sorted.length - 1, Math.max(0, Math.floor(fraction * (sorted.length - 1))));
  return sorted[position];
}
