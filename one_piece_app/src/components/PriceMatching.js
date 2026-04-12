import React, { useState, useEffect, useMemo } from 'react';
import './PriceMatching.css';
import { doc, onSnapshot, setDoc } from 'firebase/firestore';
import { db } from '../firebase';

const PriceMatching = ({ cardData }) => {
  const [unmatchedData, setUnmatchedData] = useState(null);
  const [priceHistory, setPriceHistory] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [matchValidations, setMatchValidations] = useState({});

  useEffect(() => {
    // Listen for realtime updates to match validations from Firestore
    const validationsRef = doc(db, 'price_matches', 'validations');
    const unsubscribe = onSnapshot(validationsRef, (docSnap) => {
      if (docSnap.exists()) {
        setMatchValidations(docSnap.data().matches || {});
      } else {
        setMatchValidations({});
      }
    }, (error) => {
      console.warn('Error listening to validations:', error);
    });

    return () => unsubscribe();
  }, []);

  const handleValidation = async (code, isCorrect) => {
    const status = isCorrect ? 'correct' : 'incorrect';
    const newValidations = { ...matchValidations, [code]: status };
    
    // Optimistically update local state
    setMatchValidations(newValidations);

    // Save to Firestore (not awaited to avoid blocking the UI)
    const validationsRef = doc(db, 'price_matches', 'validations');
    setDoc(validationsRef, { matches: newValidations }, { merge: true }).catch(error => {
      console.error('Error updating validation in Firestore:', error);
    });

    // Auto-advance to the next unvalidated match
    const currentIndex = confidenceMatches.findIndex(m => m.code === code);
    if (currentIndex !== -1) {
      let nextMatch = null;
      // Look forward
      for (let i = currentIndex + 1; i < confidenceMatches.length; i++) {
        if (!newValidations[confidenceMatches[i].code]) {
          nextMatch = confidenceMatches[i];
          break;
        }
      }
      // If none found forward, look from the beginning
      if (!nextMatch) {
        for (let i = 0; i < currentIndex; i++) {
          if (!newValidations[confidenceMatches[i].code]) {
            nextMatch = confidenceMatches[i];
            break;
          }
        }
      }
      setSelectedMatch(nextMatch); // will be null if all are validated, closing the modal
    }
  };

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
    if (!priceHistory || !cardData) return [];
    const matches = [];
    Object.entries(priceHistory).forEach(([code, data]) => {
      // Only show matches that haven't been validated yet
      if (data.confidence !== undefined && !matchValidations[code]) {
        const cardMatch = cardData.find(c => getImageCode(c.Picture) === code);
        matches.push({
          code,
          confidence: data.confidence,
          name: cardMatch?.Character || 'Unknown',
          picture: cardMatch?.Picture || null,
          cardrushImage: data.cardrushImage || null,
          samples: data.samples || []
        });
      }
    });
    return matches.sort((a, b) => a.confidence - b.confidence);
  }, [priceHistory, cardData, matchValidations]);

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
          {confidenceMatches.map(match => {
            const validationStatus = matchValidations[match.code];
            let statusColor = '';
            if (validationStatus === 'correct') statusColor = '4px solid #4CAF50';
            else if (validationStatus === 'incorrect') statusColor = '4px solid #F44336';

            return (
              <div 
                key={match.code} 
                className={`confidence-card ${match.confidence < 70 ? 'low' : match.confidence < 85 ? 'medium' : 'high'}`}
                onClick={() => setSelectedMatch(match)}
                style={{ cursor: 'pointer', borderBottom: statusColor }}
              >
                <div className="confidence-value">{Math.round(match.confidence)}%</div>
                <div className="confidence-details">
                  <div className="match-code">{match.code}</div>
                  <div className="match-name">{match.name}</div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {selectedMatch && (
        <div className="price-matching-overlay" onClick={() => setSelectedMatch(null)}>
          <div className="price-matching-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '800px', width: '90%' }}>
            <button className="close-btn" onClick={() => setSelectedMatch(null)}>✕</button>
            <h2>Match Details: {selectedMatch.code || 'N/A'}</h2>
            
            <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', marginBottom: '20px', flexWrap: 'wrap' }}>
              <div style={{ flex: '1 1 300px', textAlign: 'center' }}>
                <h3>Database Card</h3>
                {selectedMatch.picture ? (
                  <img 
                    src={selectedMatch.picture.includes('onepiece-cardgame.com') 
                      ? `${process.env.PUBLIC_URL}/images/cards/${selectedMatch.picture.split('?')[0].split('/').pop()}`
                      : selectedMatch.picture
                    } 
                    onError={(e) => {
                      const currentSrc = e.target.src;
                      if (currentSrc.includes('/images/cards/')) {
                        e.target.src = `https://wsrv.nl/?url=${encodeURIComponent(selectedMatch.picture.split('?')[0])}&output=webp&default=https://placehold.co/300x420?text=No+Image`;
                      } else if (currentSrc.includes('wsrv.nl')) {
                        e.target.src = 'https://placehold.co/300x420?text=No+Image';
                      }
                    }}
                    alt={selectedMatch.name || 'Card image'} 
                    style={{ width: '100%', maxWidth: '300px', borderRadius: '8px', objectFit: 'contain' }} 
                  />
                ) : (
                  <div style={{ padding: '40px', background: '#2a2e3d', borderRadius: '8px' }}>No image available</div>
                )}
                <p><strong>Mapped Name:</strong> {selectedMatch.name || 'Unknown'}</p>
              </div>
              
              <div style={{ flex: '1 1 300px', textAlign: 'center' }}>
                <h3>Cardrush Match</h3>
                {selectedMatch.cardrushImage ? (
                  <img 
                    src={selectedMatch.cardrushImage} 
                    alt="Cardrush Match" 
                    style={{ width: '100%', maxWidth: '300px', borderRadius: '8px', objectFit: 'contain' }} 
                  />
                ) : (
                  <div style={{ padding: '40px', background: '#2a2e3d', borderRadius: '8px' }}>No match image available</div>
                )}
                <p><strong>Confidence:</strong> {Math.round(selectedMatch.confidence || 0)}%</p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '15px', justifyContent: 'center', marginBottom: '20px', flexWrap: 'wrap' }}>
              <button 
                style={{ 
                  padding: '12px 24px', 
                  background: matchValidations[selectedMatch.code] === 'correct' ? '#4CAF50' : '#2a2e3d', 
                  color: 'white', 
                  border: matchValidations[selectedMatch.code] === 'correct' ? '2px solid #81c784' : '2px solid #444', 
                  borderRadius: '6px', 
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '16px'
                }}
                onClick={() => handleValidation(selectedMatch.code, true)}
              >
                Yes, this is correct match
              </button>
              <button 
                style={{ 
                  padding: '12px 24px', 
                  background: matchValidations[selectedMatch.code] === 'incorrect' ? '#F44336' : '#2a2e3d', 
                  color: 'white', 
                  border: matchValidations[selectedMatch.code] === 'incorrect' ? '2px solid #e57373' : '2px solid #444', 
                  borderRadius: '6px', 
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '16px'
                }}
                onClick={() => handleValidation(selectedMatch.code, false)}
              >
                No, incorrect match
              </button>
            </div>

            {selectedMatch.samples && selectedMatch.samples.length > 0 && (
              <div style={{ marginTop: '20px', background: '#2a2e3d', padding: '15px', borderRadius: '8px' }}>
                <strong style={{ display: 'block', marginBottom: '10px' }}>Mapping Patterns:</strong>
                <ul style={{ margin: 0, paddingLeft: '20px', color: '#ccc' }}>
                  {selectedMatch.samples.map((s, i) => <li key={i} style={{ marginBottom: '5px' }}>{s}</li>)}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

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
