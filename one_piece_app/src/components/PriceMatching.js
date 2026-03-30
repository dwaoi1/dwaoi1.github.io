import React, { useState, useEffect, useMemo } from 'react';
import './PriceMatching.css';

const PriceMatching = ({ cardData }) => {
  const [unmatchedData, setUnmatchedData] = useState(null);
  const [priceHistory, setPriceHistory] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [unmatchedRes, historyRes] = await Promise.all([
          fetch(`${process.env.PUBLIC_URL}/unmatched_prices.json`, { cache: 'no-store' }),
          fetch(`${process.env.PUBLIC_URL}/cardrush_price_history.json`, { cache: 'no-store' })
        ]);

        const unmatched = unmatchedRes.ok ? await unmatchedRes.json() : null;
        const history = historyRes.ok ? await historyRes.json() : {};

        setUnmatchedData(unmatched);
        setPriceHistory(history);
      } catch (err) {
        console.error('Error loading price matching data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const confidenceMatches = useMemo(() => {
    const matches = [];
    Object.entries(priceHistory).forEach(([code, data]) => {
      if (data.confidence !== undefined) {
        matches.push({
          code,
          confidence: data.confidence,
          // Try to find the card name from cardData if possible
          name: cardData.find(c => {
             const url = c.Picture || '';
             const filename = url.split('?')[0].substring(url.lastIndexOf('/') + 1);
             const imgCode = filename.split('.')[0];
             return imgCode === code;
          })?.Character || 'Unknown'
        });
      }
    });
    return matches.sort((a, b) => a.confidence - b.confidence); // Show lower confidence first
  }, [priceHistory, cardData]);

  if (loading) return <div className="price-matching-loading">Loading price matching data...</div>;

  return (
    <div className="price-matching-container">
      <h1>Price Matching Analysis</h1>
      <p className="description">
        This page shows potential issues with price matching and the confidence scores for automated image-based matches.
      </p>

      <section className="confidence-section">
        <h2>Automated Match Confidence</h2>
        <p className="sub-description">Showing {confidenceMatches.length} automated matches. Lower percentages may indicate incorrect mappings.</p>
        <div className="confidence-grid">
          {confidenceMatches.map(match => (
            <div key={match.code} className={`confidence-card ${match.confidence < 70 ? 'low' : match.confidence < 85 ? 'medium' : 'high'}`}>
              <div className="confidence-value">{Math.round(match.confidence)}%</div>
              <div className="confidence-details">
                <div className="match-code">{match.code}</div>
                <div className="match-name">{match.name}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {unmatchedData && (
        <section className="unmatched-section">
          <h2>Data Mismatches</h2>
          <p className="as-of">As of {unmatchedData.asOf}</p>

          <div className="unmatched-groups">
            <details className="unmatched-group" open>
              <summary>
                Cards with multiple prices ({unmatchedData.multiplePrices.length})
              </summary>
              <div className="unmatched-content">
                <ul className="unmatched-list">
                  {unmatchedData.multiplePrices.map(({ cardCode, priceCount, entries }) => (
                    <li key={cardCode} className="unmatched-item">
                      <span className="unmatched-code">{cardCode}</span>
                      <span className="unmatched-detail">
                        {priceCount} prices: {entries.map(e => `${e.name} (${e.amount})`).join(' · ')}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </details>

            <details className="unmatched-group">
              <summary>
                Prices without a matching card ({unmatchedData.pricesWithoutCards.length})
              </summary>
              <div className="unmatched-content">
                <ul className="unmatched-list">
                  {unmatchedData.pricesWithoutCards.map(({ modelNumber, latestEntries }) => (
                    <li key={modelNumber} className="unmatched-item">
                      <span className="unmatched-code">{modelNumber}</span>
                      <span className="unmatched-detail">
                        {latestEntries.map(e => `${e.name} (${e.amount})`).join(' · ')}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </details>

            <details className="unmatched-group">
              <summary>
                Cards without any price data ({unmatchedData.cardsWithoutPrices.length})
              </summary>
              <div className="unmatched-content">
                <div className="unmatched-list unmatched-list--codes">
                  {unmatchedData.cardsWithoutPrices.map(code => (
                    <span key={code} className="unmatched-code-chip">{code}</span>
                  ))}
                </div>
              </div>
            </details>
          </div>
        </section>
      )}
    </div>
  );
};

export default PriceMatching;
