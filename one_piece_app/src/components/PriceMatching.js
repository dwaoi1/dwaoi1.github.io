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

    // Auto-advance logic
    const currentIndex = allIssues.findIndex(m => m.code === code);
    if (currentIndex !== -1) {
      let nextMatch = null;
      // Look forward
      for (let i = currentIndex + 1; i < allIssues.length; i++) {
        if (!newValidations[allIssues[i].code]) {
          nextMatch = allIssues[i];
          break;
        }
      }
      // If none found forward, look from the beginning
      if (!nextMatch) {
        for (let i = 0; i < currentIndex; i++) {
          if (!newValidations[allIssues[i].code]) {
            nextMatch = allIssues[i];
            break;
          }
        }
      }
      setSelectedMatch(nextMatch);
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

  const getImageCode = (url) => {
    if (!url || typeof url !== 'string') return '';
    try {
      const path = url.split('?')[0];
      const filename = path.substring(path.lastIndexOf('/') + 1);
      return filename.split('.')[0];
    } catch (e) {
      return '';
    }
  };

  // Create a lookup map for card data by image code once
  const cardLookup = useMemo(() => {
    if (!cardData) return new Map();
    const map = new Map();
    cardData.forEach(card => {
      const code = getImageCode(card.Picture);
      if (code) map.set(code, card);
    });
    return map;
  }, [cardData]);

  const allIssues = useMemo(() => {
    if (!priceHistory || !cardData) return [];
    const issues = [];

    // 1. Add confidence-based matches
    Object.entries(priceHistory).forEach(([code, data]) => {
      if (data.confidence !== undefined && !matchValidations[code]) {
        const cardMatch = cardLookup.get(code);
        issues.push({
          code,
          type: 'confidence',
          confidence: data.confidence,
          name: cardMatch?.Character || 'Unknown',
          picture: cardMatch?.Picture || null,
          cardrushImage: data.cardrushImage || null,
          samples: data.samples || []
        });
      }
    });

    // 2. Add cards with multiple prices from unmatchedData
    if (unmatchedData && unmatchedData.multiplePrices) {
      unmatchedData.multiplePrices.forEach(item => {
        // Only show if not already validated and not already in matches
        if (!matchValidations[item.cardCode] && !issues.some(i => i.code === item.cardCode)) {
          // Find the first image code associated with this card to show an image
          const firstImgCode = item.imageCodes && item.imageCodes[0];
          const cardMatch = cardLookup.get(firstImgCode) || cardData.find(c => c.Picture.includes(item.cardCode));
          
          issues.push({
            code: item.cardCode,
            type: 'multiple',
            confidence: 0, // Special value for sorting
            name: cardMatch?.Character || 'Multiple Prices',
            picture: cardMatch?.Picture || null,
            cardrushImage: item.entries[0]?.image || null,
            entries: item.entries,
            priceCount: item.priceCount
          });
        }
      });
    }

    // Sort: Multiple price issues first, then by confidence score
    return issues.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'multiple' ? -1 : 1;
      return a.confidence - b.confidence;
    });
  }, [priceHistory, cardData, matchValidations, cardLookup, unmatchedData]);

  if (loading) return <div className="price-matching-loading">Loading price matching data...</div>;

  return (
    <div className="price-matching-container">
      <h1>Price Matching Analysis</h1>
      <p className="description">
        This page shows potential issues with price matching. Green = Correct, Red = Incorrect.
      </p>

      <section className="confidence-section">
        <h2>Validation Queue</h2>
        <p className="sub-description">Showing {allIssues.length} items requiring review. Multiple price issues are shown first.</p>
        <div className="confidence-grid">
          {allIssues.map(match => {
            const validationStatus = matchValidations[match.code];
            let statusColor = '';
            if (validationStatus === 'correct') statusColor = '4px solid #4CAF50';
            else if (validationStatus === 'incorrect') statusColor = '4px solid #F44336';

            return (
              <div 
                key={match.code} 
                className={`confidence-card ${match.type === 'multiple' ? 'multiple' : (match.confidence < 70 ? 'low' : match.confidence < 85 ? 'medium' : 'high')}`}
                onClick={() => setSelectedMatch(match)}
                style={{ cursor: 'pointer', borderBottom: statusColor }}
              >
                <div className="confidence-value">
                  {match.type === 'multiple' ? '!!!' : `${Math.round(match.confidence)}%`}
                </div>
                <div className="confidence-details">
                  <div className="match-code">{match.code}</div>
                  <div className="match-name">
                    {match.type === 'multiple' ? `Ambiguous (${match.priceCount} prices)` : match.name}
                  </div>
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
                {selectedMatch.type === 'multiple' ? (
                  <p><strong>Status:</strong> Ambiguous Match ({selectedMatch.priceCount} prices found)</p>
                ) : (
                  <p><strong>Confidence:</strong> {Math.round(selectedMatch.confidence || 0)}%</p>
                )}
              </div>
            </div>

            {selectedMatch.type === 'multiple' && selectedMatch.entries && (
              <div style={{ marginTop: '20px', background: '#1a1d26', padding: '15px', borderRadius: '8px', border: '1px solid #3a4055' }}>
                <strong style={{ display: 'block', marginBottom: '10px', color: '#63b3ed' }}>Found Multiple Price Entries:</strong>
                <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                  {selectedMatch.entries.map((e, i) => (
                    <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'center', padding: '8px', borderBottom: i < selectedMatch.entries.length - 1 ? '1px solid #2d3348' : 'none' }}>
                      <img src={e.image} alt="" style={{ width: '40px', height: 'auto', borderRadius: '4px' }} />
                      <div style={{ textAlign: 'left', fontSize: '0.9rem' }}>
                        <div style={{ color: '#e2e8f0' }}>{e.name}</div>
                        <div style={{ color: '#68d391', fontWeight: 'bold' }}>{e.amount}</div>
                      </div>
                    </div>
                  ))}
                </div>
                <p style={{ fontSize: '0.8rem', color: '#7a849a', marginTop: '10px', fontStyle: 'italic' }}>
                  Note: Marking "Incorrect" will move this card to the bottom of the list for later manual mapping.
                </p>
              </div>
            )}

            <div style={{ display: 'flex', gap: '15px', justifyContent: 'center', margin: '20px 0', flexWrap: 'wrap' }}>
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
