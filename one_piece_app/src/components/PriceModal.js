import React, { useMemo, useState, useEffect, useRef } from 'react';
import './PriceModal.css';

const TIME_RANGES = [
  { label: '14d', days: 14 },
  { label: '30d', days: 30 },
  { label: '60d', days: 60 },
  { label: '90d', days: 90 },
  { label: '180d', days: 180 },
];

const CHART_W = 700;
const CHART_H = 260;
const MARGIN = { top: 20, right: 20, bottom: 50, left: 72 };
const PLOT_W = CHART_W - MARGIN.left - MARGIN.right;
const PLOT_H = CHART_H - MARGIN.top - MARGIN.bottom;

function formatYen(value) {
  if (value >= 1000000) {
    const m = value / 1000000;
    return `¥${Number.isInteger(m) ? m : m.toFixed(1)}M`;
  }
  if (value >= 10000) return `¥${Math.round(value / 1000)}k`;
  if (value >= 1000) return `¥${(value / 1000).toFixed(1)}k`;
  return `¥${value}`;
}

function formatDate(dateStr) {
  const parts = dateStr.split('-');
  return `${parseInt(parts[1])}/${parseInt(parts[2])}`;
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

const PriceModal = ({ item, priceHistory, onClose }) => {
  const [timeRange, setTimeRange] = useState(30);
  const [showSealed, setShowSealed] = useState(true);
  const [showGoldText, setShowGoldText] = useState(true);
  const [showParallel, setShowParallel] = useState(true);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onCloseRef.current(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  const cardCode = item.cardCode;
  const histData = priceHistory[cardCode];

  // Reset variant toggles whenever a different card is opened
  useEffect(() => {
    setShowSealed(true);
    setShowGoldText(true);
    setShowParallel(true);
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

  // Build effective history from selected variant groups
  const effectiveHistory = useMemo(() => {
    return filteredHistory.map(p => {
      const allPrices = [p.minPrice, p.maxPrice].filter(v => v != null);
      if (showSealed && p.sealed) allPrices.push(p.sealed.minPrice, p.sealed.maxPrice);
      if (showGoldText && p.goldText) allPrices.push(p.goldText.minPrice, p.goldText.maxPrice);
      if (showParallel && p.parallel) allPrices.push(p.parallel.minPrice, p.parallel.maxPrice);
      const validPrices = allPrices.filter(v => v != null);
      if (validPrices.length === 0) return null;
      return {
        date: p.date,
        minPrice: Math.min(...validPrices),
        maxPrice: Math.max(...validPrices),
        count: p.count
          + (showSealed && p.sealed ? p.sealed.count : 0)
          + (showGoldText && p.goldText ? p.goldText.count : 0)
          + (showParallel && p.parallel ? p.parallel.count : 0),
      };
    }).filter(Boolean);
  }, [filteredHistory, showSealed, showGoldText, showParallel]);

  const chart = useMemo(() => {
    if (effectiveHistory.length === 0) return null;

    const prices = effectiveHistory.map(p => p.minPrice);
    const maxPrices = effectiveHistory.map(p => p.maxPrice);
    const dataMinPrice = Math.min(...prices);
    const dataMaxPrice = Math.max(...maxPrices);
    const priceRange = dataMaxPrice - dataMinPrice;

    const yMin = dataMinPrice - priceRange * 0.1;
    const yMax = dataMaxPrice + priceRange * 0.1;
    const yRange = yMax - yMin || 1;

    const n = effectiveHistory.length;
    const xScale = (i) =>
      MARGIN.left + (n > 1 ? (i / (n - 1)) * PLOT_W : PLOT_W / 2);
    const yScale = (price) =>
      MARGIN.top + PLOT_H - ((price - yMin) / yRange) * PLOT_H;

    const minPoints = effectiveHistory
      .map((p, i) => `${xScale(i)},${yScale(p.minPrice)}`)
      .join(' ');

    const hasRange = effectiveHistory.some(p => p.count > 1 && p.minPrice !== p.maxPrice);
    const areaPoints = hasRange
      ? [
          ...effectiveHistory.map((p, i) => `${xScale(i)},${yScale(p.maxPrice)}`),
          ...effectiveHistory
            .slice()
            .reverse()
            .map((p, i, arr) => `${xScale(arr.length - 1 - i)},${yScale(p.minPrice)}`),
        ].join(' ')
      : null;

    const yTicks = niceTicks(dataMinPrice, dataMaxPrice, 5);

    const xTickIndices = [];
    if (n <= 8) {
      for (let i = 0; i < n; i++) xTickIndices.push(i);
    } else {
      const step = Math.ceil(n / 7);
      for (let i = 0; i < n; i += step) xTickIndices.push(i);
      if (xTickIndices[xTickIndices.length - 1] !== n - 1) xTickIndices.push(n - 1);
    }

    return { minPoints, areaPoints, xScale, yScale, yTicks, xTickIndices, hasRange };
  }, [effectiveHistory]);

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

        <div className="price-modal-header">
          <img
            src={item.Picture}
            alt={item.Character}
            className="price-modal-card-image"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
          <div className="price-modal-header-info">
            <span className="price-modal-code">{cardCode}</span>
            <span className="price-modal-character">{item.Character}</span>
          </div>
        </div>

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

        {(hasSealed || hasGoldText || hasParallel) && (
          <div className="price-modal-variant-filters">
            {hasParallel && (
              <label className="variant-filter-label">
                <input
                  type="checkbox"
                  checked={showParallel}
                  onChange={e => setShowParallel(e.target.checked)}
                />
                <span className="variant-filter-dot variant-filter-dot--parallel" />
                Parallel (パラレル)
              </label>
            )}
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
          </div>
        )}

        {!histData || effectiveHistory.length === 0 ? (
          <div className="price-modal-no-data">
            {!histData
              ? 'No price data available for this card.'
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
              {chart.xTickIndices.map(i => (
                <text
                  key={i}
                  x={chart.xScale(i)}
                  y={MARGIN.top + PLOT_H + 16}
                  textAnchor="middle"
                  fontSize="10"
                  fill="#9ca4b7"
                  transform={`rotate(-35,${chart.xScale(i)},${MARGIN.top + PLOT_H + 16})`}
                >
                  {formatDate(effectiveHistory[i].date)}
                </text>
              ))}

              {/* Price range shaded area */}
              {chart.areaPoints && (
                <polygon
                  points={chart.areaPoints}
                  fill="rgba(99,179,237,0.12)"
                />
              )}

              {/* Price line */}
              <polyline
                points={chart.minPoints}
                fill="none"
                stroke="#63b3ed"
                strokeWidth="2"
                strokeLinejoin="round"
                strokeLinecap="round"
              />

              {/* Data point dots */}
              {effectiveHistory.map((p, i) => (
                <circle
                  key={i}
                  cx={chart.xScale(i)}
                  cy={chart.yScale(p.minPrice)}
                  r="3"
                  fill="#63b3ed"
                >
                  <title>
                    {p.date}: {formatYen(p.minPrice)}
                    {p.count > 1
                      ? ` – ${formatYen(p.maxPrice)} (${p.count} price entries)`
                      : ''}
                  </title>
                </circle>
              ))}
            </svg>

            {chart.hasRange && (
              <p className="price-chart-note">
                Shaded area shows price range across multiple variants. Line shows lowest price.
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
  );
};

export default PriceModal;
