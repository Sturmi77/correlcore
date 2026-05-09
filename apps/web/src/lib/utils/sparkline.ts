/**
 * Sparkline path builder — ADR-0014.
 *
 * Pure SVG path math for the 14-day mood sparkline. We hand-roll this
 * instead of pulling in uPlot/Chart.js/ApexCharts for the cost reasons
 * laid out in ADR-0014: ~80 LOC vs. 45–400 KB gzip.
 *
 * The output deliberately separates the *solid* segments (consecutive
 * days both have data) from *dashed* segments (one or both endpoints
 * are missing) so the renderer can apply different `stroke-dasharray`
 * patterns per polyline.
 *
 * Coordinate space:
 *  - x: pixel space, evenly spaced over the requested chart width
 *  - y: inverted from value space (`min` at the bottom = `height`,
 *    `max` at the top = 0) with a 2 px padding so circles aren't
 *    clipped at the edges
 */

export interface SparklinePoint {
  /** ISO date YYYY-MM-DD — used for `<title>` tooltips and key. */
  date: string;
  /** Numeric value (e.g. mood 1–5) or `null` for missing days. */
  value: number | null;
}

export interface SparklineGeometry {
  width: number;
  height: number;
  /** All point coordinates in screen-space, including missing values
   *  (those just don't get a circle drawn). */
  coords: { date: string; x: number; y: number | null; value: number | null }[];
  /** Solid segments — consecutive days where *both* endpoints have data. */
  solidSegments: { x1: number; y1: number; x2: number; y2: number }[];
  /** Dashed segments — bridge over missing data points so the trend
   *  line stays visible without giving false precision. */
  dashedSegments: { x1: number; y1: number; x2: number; y2: number }[];
}

const PAD = 2;

/**
 * Build the geometry for a sparkline.
 *
 * @param points  ordered oldest → newest
 * @param width   total SVG width in CSS pixels
 * @param height  total SVG height in CSS pixels
 * @param min     value-space minimum (e.g. mood 1)
 * @param max     value-space maximum (e.g. mood 5)
 */
export function buildSparkline(
  points: readonly SparklinePoint[],
  width: number,
  height: number,
  min: number,
  max: number
): SparklineGeometry {
  const w = Math.max(width, 1);
  const h = Math.max(height, 1);
  const innerH = Math.max(h - 2 * PAD, 1);
  const span = Math.max(max - min, 1);

  const n = points.length;
  const coords: SparklineGeometry['coords'] = [];
  if (n === 0) return { width: w, height: h, coords, solidSegments: [], dashedSegments: [] };

  const stepX = n === 1 ? 0 : w / (n - 1);

  for (let i = 0; i < n; i += 1) {
    const p = points[i];
    const x = n === 1 ? w / 2 : i * stepX;
    let y: number | null = null;
    if (p.value !== null && Number.isFinite(p.value)) {
      // Clamp into [min, max] before scaling so an out-of-range
      // datapoint can't escape the box.
      const v = Math.min(Math.max(p.value, min), max);
      const norm = (v - min) / span; // 0..1
      y = PAD + (1 - norm) * innerH;
    }
    coords.push({ date: p.date, x, y, value: p.value });
  }

  const solid: SparklineGeometry['solidSegments'] = [];
  const dashed: SparklineGeometry['dashedSegments'] = [];

  // Walk pairs (i, i+1). If both have a y, build a solid segment.
  // Otherwise, find the nearest non-null neighbours on either side and
  // draw a dashed bridge between them so the eye still gets the trend.
  for (let i = 0; i < n - 1; i += 1) {
    const a = coords[i];
    const b = coords[i + 1];
    if (a.y !== null && b.y !== null) {
      solid.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });
    }
  }

  // Dashed bridges: for every pair of adjacent non-null points that
  // are *not* immediate neighbours (gap of >= 1 missing day between
  // them), draw a dashed segment between them. Single missing days
  // between two known points → one dashed segment.
  let lastFilledIdx = -1;
  for (let i = 0; i < n; i += 1) {
    if (coords[i].y !== null) {
      if (lastFilledIdx >= 0 && i - lastFilledIdx >= 2) {
        const a = coords[lastFilledIdx];
        const b = coords[i];
        if (a.y !== null && b.y !== null) {
          dashed.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });
        }
      }
      lastFilledIdx = i;
    }
  }

  return { width: w, height: h, coords, solidSegments: solid, dashedSegments: dashed };
}
