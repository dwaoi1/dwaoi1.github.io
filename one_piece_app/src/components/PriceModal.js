import React, { useMemo, useState, useEffect, useRef } from 'react';
import './PriceModal.css';
import { getProxiedImageUrl } from '../utils/imageUtils';

const TIME_RANGES = [
  { label: '30d', days: 30 },
  { label: '60d', days: 60 },
  { label: '90d', days: 90 },
  { label: '180d', days: 180 },
  { label: '1y', days: 365 },
  { label: '2y', days: 730 },
];

const CHART_W = 700;
const CHART_H = 390;
const MARGIN = { top: 20, right: 20, bottom: 50, left: 72 };
const PLOT_W = CHART_W - MARGIN.left - MARGIN.right;
const PLOT_H = CHART_H - MARGIN.top - MARGIN.bottom;
const DAY_MS = 24 * 60 * 60 * 1000;
// Max number of consecutive missing dates still bridged with a line.
// Gaps longer than this render as blank space.
const MAX_BRIDGE_MISSING_DAYS = 3;
const X_TICK_COUNT = 7;

function formatYen(value) {
  if (value >= 1000000) {
    const m = value / 1000000;
    return `¥${Number.isInteger(m) ? m : m.toFixed(1)}M`;
  }
  if (value >= 10000) return `¥${Math.round(value / 1000)}k`;
  if (value >= 1000) return `¥${(value / 1000).toFixed(1)}k`;
  return `¥${value}`;
}

function formatFullDate(dateStr) {
  return dateStr.replace(/-/g, '/');
}

function formatAxisDate(dateStr) {
  const parts = dateStr.split('-');
  return `${parts[1]}/${parts[2]}`;
}

function niceTicks(minVal, maxVal, count) {
  if (minVal === maxVal) return [minVal];
  const range = maxVal - minVal;
  const roughStep = range / (count - 1);
  const mag = Math.pow(10, Math.floor(Math.log10(roughStep)));
  const nicedStep = Math.ceil(roughStep / mag) * mag;
  const start = Math.floor(minVal / nicedStep) * nicedStep;
  const ticks = [];
  for (let t = start; t <= maxVal + nicedStep * 0.01; t += nicedStep) {
    ticks.push(Math.round(t));
    if (ticks.length > count + 2) break;
  }
  return ticks.filter(t => t >= 0);
}

// Extract image code from a card picture URL, e.g. 'OP01-051_p1' from '.../OP01-051_p1.png?...'
// Handles both standard codes (OP03-001, OP01-051_p2) and promo codes (P-028, P-028_p1).
function getImageCode(url) {
  if (!url) return '';
  const m = url.match(/\/([A-Z]{2,}\d{2,}-\d{3}(?:_p\d*)?|[A-Z]-\d{3}(?:_p\d*)?)\.[^/]+(\?|$)/);
  return m ? m[1] : '';
}

// Build a human-readable tooltip label for a price data point.
// prefix: optional context string e.g. '' for base, 'Sealed', 'Gold text'
function makeTooltipLabel(prefix, p) {
  const dateStr = [prefix, formatFullDate(p.date)].filter(Boolean).join(' ');
  return p.count > 1
    ? `${dateStr}: ${formatYen(p.minPrice)} – ${formatYen(p.maxPrice)} (${p.count} entries)`
    : `${dateStr}: ${formatYen(p.minPrice)}`;
}

const PriceModal = ({ item, priceHistory, onClose }) => {
  const [timeRange, setTimeRange] = useState(180);
  const [showSealed, setShowSealed] = useState(true);
  const [showGoldText, setShowGoldText] = useState(true);
  const [showAsia, setShowAsia] = useState(true);
  const [showSealedAsia, setShowSealedAsia] = useState(true);
  const [tooltip, setTooltip] = useState(null); // { x, y, text }
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onCloseRef.current(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  const cardCode = item.cardCode;

  // Detect if this card is a parallel (URL has _p suffix).
  // For parallel cards we show p.parallel as the primary data source.
  const imageCode = getImageCode(item.Picture);
  const isParallelCard = /_p\d*$/.test(imageCode);

  // Look up price history by image code first (used when per-image overrides were built).
  // Fall back to the shared card code for both parallel and base cards.
  const hasImageCodeEntry = Boolean(priceHistory[imageCode]);
  const histData = priceHistory[imageCode] || priceHistory[cardCode];

  // Reset variant toggles whenever a different card is opened
  useEffect(() => {
    setShowSealed(true);
    setShowGoldText(true);
    setShowAsia(true);
    setShowSealedAsia(true);
  }, [cardCode]);

  const filteredHistory = useMemo(() => {
    if (!histData || !histData.history.length) return [];
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - timeRange);
    const cutoffStr = cutoff.toISOString().slice(0, 10);
    return histData.history.filter(p => p.date >= cutoffStr);
  }, [histData, timeRange]);

  // Determine which variant types are available in the filtered window
  const hasSealed = useMemo(() => filteredHistory.some(p => p.sealed), [filteredHistory]);
  const hasGoldText = useMemo(() => filteredHistory.some(p => p.goldText), [filteredHistory]);
  const hasParallel = useMemo(() => filteredHistory.some(p => p.parallel), [filteredHistory]);
  const hasAsia = useMemo(() => filteredHistory.some(p => p.asia || p.parallelAsia), [filteredHistory]);
  const hasSealedAsia = useMemo(() => filteredHistory.some(p => p.sealedAsia), [filteredHistory]);

  // Base price history.
  // For parallel card images (_p suffix) that have parallel subgroup data:
  //   show only p.parallel, since the user wants the parallel-specific price.
  const effectiveHistory = useMemo(() => {
    if (isParallelCard && hasParallel) {
      return filteredHistory
        .filter(p => p.parallel)
        .map(p => ({
          date: p.date,
          minPrice: p.parallel.minPrice,
          maxPrice: p.parallel.maxPrice,
          count: p.parallel.count,
        }));
    }
    // Parallel card falling back to base code with no parallel subgroup: show nothing.
    if (isParallelCard && !hasImageCodeEntry) {
      return [];
    }
    // Base cards: only the root base prices (count > 0 means at least one base entry).
    return filteredHistory
      .filter(p => p.minPrice != null && p.count > 0)
      .map(p => ({
        date: p.date,
        minPrice: p.minPrice,
        maxPrice: p.maxPrice,
        count: p.count,
      }));
  }, [filteredHistory, isParallelCard, hasParallel, hasImageCodeEntry]);

  // Sealed price series – shown as a separate orange line on the chart.
  const sealedSeries = useMemo(() => {
    if ((isParallelCard && !hasImageCodeEntry) || !showSealed) return [];
    return filteredHistory
      .filter(p => p.sealed)
      .map(p => ({
        date: p.date,
        minPrice: p.sealed.minPrice,
        maxPrice: p.sealed.maxPrice,
        count: p.sealed.count,
      }));
  }, [filteredHistory, isParallelCard, hasImageCodeEntry, showSealed]);

  // Gold text price series – shown as a separate gold/yellow line on the chart.
  const goldTextSeries = useMemo(() => {
    if ((isParallelCard && !hasImageCodeEntry) || !showGoldText) return [];
    return filteredHistory
      .filter(p => p.goldText)
      .map(p => ({
        date: p.date,
        minPrice: p.goldText.minPrice,
        maxPrice: p.goldText.maxPrice,
        count: p.goldText.count,
      }));
  }, [filteredHistory, isParallelCard, hasImageCodeEntry, showGoldText]);

  // Asia (Opened) series – shown as a separate purple line.
  const asiaSeries = useMemo(() => {
    if ((isParallelCard && !hasImageCodeEntry) || !showAsia) return [];
    return filteredHistory
      .filter(p => p.asia || p.parallelAsia)
      .map(p => {
        const d = p.parallelAsia || p.asia;
        return {
          date: p.date,
          minPrice: d.minPrice,
          maxPrice: d.maxPrice,
          count: d.count,
        };
      });
  }, [filteredHistory, isParallelCard, hasImageCodeEntry, showAsia]);

  // Asia (Sealed) series – shown as a separate green line.
  const sealedAsiaSeries = useMemo(() => {
    if ((isParallelCard && !hasImageCodeEntry) || !showSealedAsia) return [];
    return filteredHistory
      .filter(p => p.sealedAsia)
      .map(p => ({
        date: p.date,
        minPrice: p.sealedAsia.minPrice,
        maxPrice: p.sealedAsia.maxPrice,
        count: p.sealedAsia.count,
      }));
  }, [filteredHistory, isParallelCard, hasImageCodeEntry, showSealedAsia]);

  const chart = useMemo(() => {
    const n = filteredHistory.length;
    if (n === 0) return null;

    // Collect all prices from every visible series to compute a unified Y scale.
    const allPrices = [effectiveHistory, sealedSeries, goldTextSeries, asiaSeries, sealedAsiaSeries].flatMap(series =>
      series.flatMap(p => [p.minPrice, p.maxPrice].filter(v => v != null))
    );
    if (allPrices.length === 0) return null;

    const dataMinPrice = Math.min(...allPrices);
    const dataMaxPrice = Math.max(...allPrices);
    const priceRange = dataMaxPrice - dataMinPrice;

    const yMin = dataMinPrice - priceRange * 0.1;
    const yMax = dataMaxPrice + priceRange * 0.1;
    const yRange = yMax - yMin || 1;

    // Calendar-proportional x scale: dates with no data occupy real space
    // instead of being squished together.
    const t0 = Date.parse(filteredHistory[0].date);
    const t1 = Date.parse(filteredHistory[n - 1].date);
    const xScale = (dateStr) =>
      t1 > t0
        ? MARGIN.left + ((Date.parse(dateStr) - t0) / (t1 - t0)) * PLOT_W
        : MARGIN.left + PLOT_W / 2;
    const yScale = (price) =>
      MARGIN.top + PLOT_H - ((price - yMin) / yRange) * PLOT_H;

    // Filter yTicks to ensure grid lines only appear within the plot area
    const yTicks = niceTicks(dataMinPrice, dataMaxPrice, 5).filter(
      t => yScale(t) >= MARGIN.top && yScale(t) <= MARGIN.top + PLOT_H
    );

    // Split a series into segments whenever more than MAX_BRIDGE_MISSING_DAYS
    // consecutive dates have no data, leaving blank space across long gaps.
    const splitSegments = (series) => {
      const segments = [];
      let current = [];
      series.forEach((p, i) => {
        if (i > 0) {
          const missing = (Date.parse(p.date) - Date.parse(series[i - 1].date)) / DAY_MS - 1;
          if (missing > MAX_BRIDGE_MISSING_DAYS) {
            segments.push(current);
            current = [];
          }
        }
        current.push(p);
      });
      if (current.length) segments.push(current);
      return segments;
    };

    // Helper: convert a series to an array of polyline points strings.
    const toPoints = (series) =>
      splitSegments(series)
        .filter(seg => seg.length >= 2)
        .map(seg => seg.map(p => `${xScale(p.date)},${yScale(p.minPrice)}`).join(' '));

    // Helper: precompute dot positions for a series.
    const toDots = (series) =>
      series.map(p => ({
        ...p,
        cx: xScale(p.date),
        cy: yScale(p.minPrice),
      }));

    // Base line
    const minPoints = toPoints(effectiveHistory);
    const hasRange = effectiveHistory.some(p => p.count > 1 && p.minPrice !== p.maxPrice);
    const areaPoints = hasRange
      ? splitSegments(effectiveHistory)
          .filter(seg => seg.length >= 2)
          .map(seg =>
            [
              ...seg.map(p => `${xScale(p.date)},${yScale(p.maxPrice)}`),
              ...seg
                .slice()
                .reverse()
                .map(p => `${xScale(p.date)},${yScale(p.minPrice)}`),
            ].join(' ')
          )
      : [];

    // Calendar-based x-axis ticks, evenly spaced across the time range.
    const xTicks = (() => {
      if (t1 <= t0) {
        const date = filteredHistory[0].date;
        return [{ date, x: xScale(date) }];
      }
      const ticks = [];
      for (let k = 0; k <= X_TICK_COUNT; k++) {
        const date = new Date(t0 + ((t1 - t0) * k) / X_TICK_COUNT).toISOString().slice(0, 10);
        if (ticks.length && ticks[ticks.length - 1].date === date) continue;
        ticks.push({ date, x: xScale(date) });
      }
      return ticks;
    })();

    return {
      minPoints, areaPoints,
      sealedPoints: toPoints(sealedSeries),
      goldPoints: toPoints(goldTextSeries),
      asiaPoints: toPoints(asiaSeries),
      sealedAsiaPoints: toPoints(sealedAsiaSeries),
      effectiveDots: toDots(effectiveHistory),
      sealedDots: toDots(sealedSeries),
      goldDots: toDots(goldTextSeries),
      asiaDots: toDots(asiaSeries),
      sealedAsiaDots: toDots(sealedAsiaSeries),
      yScale, yTicks, xTicks, hasRange,
    };
  }, [filteredHistory, effectiveHistory, sealedSeries, goldTextSeries, asiaSeries, sealedAsiaSeries]);

  const latestPoint = effectiveHistory[effectiveHistory.length - 1];

  return (
    <div
      className="price-modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Price history for ${cardCode}`}
    >
      <div className="price-modal" onClick={e => e.stopPropagation()}>
        <button className="price-modal-close" onClick={onClose} aria-label="Close">
          ✕
        </button>

        <div className="price-modal-title-row">
          <span className="price-modal-code">{cardCode}</span>
          <span className="price-modal-character">{item.Character}</span>
        </div>

        <div className="price-modal-body">
          {/* Left panel: card image */}
          <div className="price-modal-card-panel">
            <img
              src={getProxiedImageUrl(item.Picture)}
              alt={item.Character}
              className="price-modal-card-image-large"
              referrerPolicy="no-referrer"
              data-blur
              onLoad={(e) => { e.target.setAttribute('data-loaded', ''); }}
              onError={(e) => {
                const currentSrc = e.target.src;
                if (currentSrc.includes('placehold')) return;

                const historyEntry = priceHistory[item.imageCode] || priceHistory[item.cardCode];
                const crFallback = historyEntry?.cardrushImage;
                const cleanUrl = item.Picture.split('?')[0];
                const encodedUrl = encodeURIComponent(cleanUrl);

                if (currentSrc.includes('wsrv.nl')) {
                  e.target.src = `${process.env.PUBLIC_URL}/images/cards/${item.cardId}`;
                } else if (currentSrc.includes('/images/cards/')) {
                  if (crFallback) {
                    e.target.src = crFallback;
                  } else {
                    e.target.src = `https://images.weserv.nl/?url=${encodedUrl}&output=webp&default=https://placehold.co/150?text=No+Image`;
                  }
                } else {
                  e.target.src = 'https://placehold.co/150?text=No+Image';
                }
              }}
            />
          </div>

          {/* Right panel: controls + chart */}
          <div className="price-modal-right-panel">
            <div className="price-modal-time-range">
              {TIME_RANGES.map(({ label, days }) => (
                <button
                  key={label}
                  className={`time-range-btn${timeRange === days ? ' active' : ''}`}
                  onClick={() => setTimeRange(days)}
                >
                  {label}
                </button>
              ))}
            </div>

            {(hasSealed || hasGoldText || hasAsia || hasSealedAsia) && (
              <div className="price-modal-variant-filters">
                {hasSealed && (
                  <label className="variant-filter-label">
                    <input
                      type="checkbox"
                      checked={showSealed}
                      onChange={e => setShowSealed(e.target.checked)}
                    />
                    <span className="variant-filter-dot variant-filter-dot--sealed" />
                    Sealed (未開封)
                  </label>
                )}
                {hasGoldText && (
                  <label className="variant-filter-label">
                    <input
                      type="checkbox"
                      checked={showGoldText}
                      onChange={e => setShowGoldText(e.target.checked)}
                    />
                    <span className="variant-filter-dot variant-filter-dot--gold" />
                    Gold text (金文字)
                  </label>
                )}
                {hasSealedAsia && (
                  <label className="variant-filter-label">
                    <input
                      type="checkbox"
                      checked={showSealedAsia}
                      onChange={e => setShowSealedAsia(e.target.checked)}
                    />
                    <span className="variant-filter-dot variant-filter-dot--sealed-asia" />
                    Sealed Asia
                  </label>
                )}
                {hasAsia && (
                  <label className="variant-filter-label">
                    <input
                      type="checkbox"
                      checked={showAsia}
                      onChange={e => setShowAsia(e.target.checked)}
                    />
                    <span className="variant-filter-dot variant-filter-dot--asia" />
                    Opened Asia
                  </label>
                )}
              </div>
            )}

            {!histData || !chart ? (
              <div className="price-modal-no-data">
                {!histData
                  ? 'No price data available for this card.'
                  : isParallelCard
                    ? `No parallel price data available in the last ${timeRange} days.`
                    : `No price data available in the last ${timeRange} days.`}
              </div>
            ) : (
              <div className="price-chart-container">
                <svg
                  viewBox={`0 0 ${CHART_W} ${CHART_H}`}
                  className="price-chart-svg"
                  aria-hidden="true"
                >
                  {/* Grid lines */}
                  {chart.yTicks.map(tick => (
                    <line
                      key={tick}
                      x1={MARGIN.left}
                      y1={chart.yScale(tick)}
                      x2={MARGIN.left + PLOT_W}
                      y2={chart.yScale(tick)}
                      stroke="#2a2f3f"
                      strokeWidth="1"
                    />
                  ))}

                  {/* Axes */}
                  <line
                    x1={MARGIN.left} y1={MARGIN.top}
                    x2={MARGIN.left} y2={MARGIN.top + PLOT_H}
                    stroke="#4a5169" strokeWidth="1"
                  />
                  <line
                    x1={MARGIN.left} y1={MARGIN.top + PLOT_H}
                    x2={MARGIN.left + PLOT_W} y2={MARGIN.top + PLOT_H}
                    stroke="#4a5169" strokeWidth="1"
                  />

                  {/* Y axis labels */}
                  {chart.yTicks.map(tick => (
                    <text
                      key={tick}
                      x={MARGIN.left - 6}
                      y={chart.yScale(tick) + 4}
                      textAnchor="end"
                      fontSize="11"
                      fill="#9ca4b7"
                    >
                      {formatYen(tick)}
                    </text>
                  ))}

                  {/* X axis labels */}
                  {chart.xTicks.map(tick => (
                    <text
                      key={tick.date}
                      x={tick.x}
                      y={MARGIN.top + PLOT_H + 16}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#9ca4b7"
                      transform={`rotate(-35,${tick.x},${MARGIN.top + PLOT_H + 16})`}
                    >
                      {formatAxisDate(tick.date)}
                    </text>
                  ))}

                  {/* Base price range shaded area (one polygon per segment) */}
                  {chart.areaPoints.map((pts, i) => (
                    <polygon
                      key={`area-${i}`}
                      points={pts}
                      fill="rgba(99,179,237,0.12)"
                    />
                  ))}

                  {/* Base price line (blue) */}
                  {chart.minPoints.map((pts, i) => (
                    <polyline
                      key={`base-line-${i}`}
                      points={pts}
                      fill="none"
                      stroke="#63b3ed"
                      strokeWidth="2"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                  ))}

                  {/* Sealed price line (orange) */}
                  {chart.sealedPoints.map((pts, i) => (
                    <polyline
                      key={`sealed-line-${i}`}
                      points={pts}
                      fill="none"
                      stroke="#ed8936"
                      strokeWidth="2"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                  ))}

                  {/* Gold text price line (gold/yellow) */}
                  {chart.goldPoints.map((pts, i) => (
                    <polyline
                      key={`gold-line-${i}`}
                      points={pts}
                      fill="none"
                      stroke="#ecc94b"
                      strokeWidth="2"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                  ))}

                  {/* Asia Opened line (purple) */}
                  {chart.asiaPoints.map((pts, i) => (
                    <polyline
                      key={`asia-line-${i}`}
                      points={pts}
                      fill="none"
                      stroke="#9f7aea"
                      strokeWidth="2"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                  ))}

                  {/* Asia Sealed line (green) */}
                  {chart.sealedAsiaPoints.map((pts, i) => (
                    <polyline
                      key={`sealedAsia-line-${i}`}
                      points={pts}
                      fill="none"
                      stroke="#48bb78"
                      strokeWidth="2"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                  ))}

                  {/* Base data point dots */}
                  {chart.effectiveDots.map((p, i) => {
                    const label = makeTooltipLabel('', p);
                    return (
                      <circle
                        key={`base-${i}`}
                        cx={p.cx}
                        cy={p.cy}
                        r="4"
                        fill="#63b3ed"
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={(e) => {
                          const svg = e.currentTarget.closest('svg');
                          const rect = svg.getBoundingClientRect();
                          const scaleX = rect.width / CHART_W;
                          const scaleY = rect.height / CHART_H;
                          setTooltip({
                            x: rect.left + p.cx * scaleX,
                            y: rect.top + p.cy * scaleY - 12,
                            text: label,
                          });
                        }}
                        onMouseLeave={() => setTooltip(null)}
                      />
                    );
                  })}

                  {/* Sealed data point dots (orange) */}
                  {chart.sealedDots.map((p, i) => {
                    const label = makeTooltipLabel('Sealed', p);
                    return (
                      <circle
                        key={`sealed-${i}`}
                        cx={p.cx}
                        cy={p.cy}
                        r="4"
                        fill="#ed8936"
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={(e) => {
                          const svg = e.currentTarget.closest('svg');
                          const rect = svg.getBoundingClientRect();
                          const scaleX = rect.width / CHART_W;
                          const scaleY = rect.height / CHART_H;
                          setTooltip({
                            x: rect.left + p.cx * scaleX,
                            y: rect.top + p.cy * scaleY - 12,
                            text: label,
                          });
                        }}
                        onMouseLeave={() => setTooltip(null)}
                      />
                    );
                  })}

                  {/* Gold text data point dots (gold/yellow) */}
                  {chart.goldDots.map((p, i) => {
                    const label = makeTooltipLabel('Gold text', p);
                    return (
                      <circle
                        key={`gold-${i}`}
                        cx={p.cx}
                        cy={p.cy}
                        r="4"
                        fill="#ecc94b"
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={(e) => {
                          const svg = e.currentTarget.closest('svg');
                          const rect = svg.getBoundingClientRect();
                          const scaleX = rect.width / CHART_W;
                          const scaleY = rect.height / CHART_H;
                          setTooltip({
                            x: rect.left + p.cx * scaleX,
                            y: rect.top + p.cy * scaleY - 12,
                            text: label,
                          });
                        }}
                        onMouseLeave={() => setTooltip(null)}
                      />
                    );
                  })}

                  {/* Asia Opened data point dots (purple) */}
                  {chart.asiaDots.map((p, i) => {
                    const label = makeTooltipLabel('Asia', p);
                    return (
                      <circle
                        key={`asia-${i}`}
                        cx={p.cx}
                        cy={p.cy}
                        r="4"
                        fill="#9f7aea"
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={(e) => {
                          const svg = e.currentTarget.closest('svg');
                          const rect = svg.getBoundingClientRect();
                          const scaleX = rect.width / CHART_W;
                          const scaleY = rect.height / CHART_H;
                          setTooltip({
                            x: rect.left + p.cx * scaleX,
                            y: rect.top + p.cy * scaleY - 12,
                            text: label,
                          });
                        }}
                        onMouseLeave={() => setTooltip(null)}
                      />
                    );
                  })}

                  {/* Asia Sealed data point dots (green) */}
                  {chart.sealedAsiaDots.map((p, i) => {
                    const label = makeTooltipLabel('Sealed Asia', p);
                    return (
                      <circle
                        key={`sealedAsia-${i}`}
                        cx={p.cx}
                        cy={p.cy}
                        r="4"
                        fill="#48bb78"
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={(e) => {
                          const svg = e.currentTarget.closest('svg');
                          const rect = svg.getBoundingClientRect();
                          const scaleX = rect.width / CHART_W;
                          const scaleY = rect.height / CHART_H;
                          setTooltip({
                            x: rect.left + p.cx * scaleX,
                            y: rect.top + p.cy * scaleY - 12,
                            text: label,
                          });
                        }}
                        onMouseLeave={() => setTooltip(null)}
                      />
                    );
                  })}
                </svg>

                {chart.hasRange && (
                  <p className="price-chart-note">
                    Shaded area shows base price range. Line shows lowest price.
                  </p>
                )}
              </div>
            )}

            {latestPoint && (
              <div className="price-modal-latest">
                Latest:{' '}
                <strong>{formatYen(latestPoint.minPrice)}</strong>
                {latestPoint.count > 1 && (
                  <span className="price-modal-variants">
                    {' '}({latestPoint.count} price entries, up to {formatYen(latestPoint.maxPrice)})
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
      {tooltip && (
        <div
          className="price-chart-tooltip"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
};

export default PriceModal;
