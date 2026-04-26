import React, { useState, useMemo, useEffect, useCallback } from 'react';
import './CardTable.css';
import PriceModal from './PriceModal';
import { doc, onSnapshot, setDoc } from 'firebase/firestore';
import { db } from '../firebase';

const CardTable = ({ data }) => {
  const [selectedCharacter, setSelectedCharacter] = useState('');
  const [selectedColor, setSelectedColor] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('character');
  const [wishlistOnly, setWishlistOnly] = useState(false);
  const [wishlist, setWishlist] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [priceModal, setPriceModal] = useState(null);
  const [priceHistory, setPriceHistory] = useState({});
  const itemsPerPage = 100;

  const getCardCode = (url) => {
    if (!url || typeof url !== 'string') return '';
    const match = url.match(/\/([A-Z]{2,}\d{2,}-\d{3}|[A-Z]-\d{3})/);
    return match ? match[1] : '';
  };

  const getCardFilename = (url) => {
    if (!url || typeof url !== 'string') return '';
    try {
      const path = url.split('?')[0];
      return path.substring(path.lastIndexOf('/') + 1);
    } catch (e) {
      return '';
    }
  };

  const getImageCode = useCallback((url) => {
    const filename = getCardFilename(url);
    if (!filename) return '';
    return filename.split('.')[0];
  }, []);

  const getSeriesCode = (cardCode) => (cardCode ? cardCode.split('-')[0] : '');

  const formatSeriesLabel = (seriesCode) => {
    if (!seriesCode) {
      return 'Promos/Unknown';
    }
    const match = seriesCode.match(/^([A-Z]+)(\d{2})$/);
    return match ? `${match[1]}-${match[2]}` : seriesCode;
  };

  const normalizeCharacter = (character) => {
    if (!character) {
      return '';
    }
    // 1. Remove (parallel) suffix
    let normalized = character.replace(/\s*\(parallel\)\s*$/i, '');
    
    // 2. Systematic normalization of characters
    // Convert full-width Ｄ to half-width D (common in One Piece card names)
    normalized = normalized.replace(/Ｄ/g, 'D');
    
    // 3. Optional: normalize other common punctuation if needed
    // normalized = normalized.replace(/・/g, '.'); // keeping katakana middle dot for now as it's standard
    
    return normalized.trim();
  };

  useEffect(() => {
    // Listen for realtime updates to the global wishlist from Firestore
    const wishlistRef = doc(db, 'wishlists', 'global');
    const unsubscribe = onSnapshot(wishlistRef, (docSnap) => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        if (Array.isArray(data.items)) {
          const normalized = data.items.map(getCardFilename).filter(Boolean);
          setWishlist(normalized);
        }
      } else {
        // If the document doesn't exist yet, we can start with an empty array
        setWishlist([]);
      }
    }, (error) => {
      console.warn('Error listening to wishlist:', error);
    });

    return () => unsubscribe();
  }, []);

  const toggleWishlist = async (cardId) => {
    const newWishlist = wishlist.includes(cardId)
      ? wishlist.filter((id) => id !== cardId)
      : [...wishlist, cardId];
    
    // Optimistically update local state
    setWishlist(newWishlist);

    // Save to Firestore
    try {
      const wishlistRef = doc(db, 'wishlists', 'global');
      await setDoc(wishlistRef, { items: newWishlist });
    } catch (error) {
      console.error('Error updating wishlist in Firestore:', error);
    }
  };

  useEffect(() => {
    let isMounted = true;
    fetch(`${process.env.PUBLIC_URL}/cardrush_price_history.json`, { cache: 'no-store' })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d && isMounted) setPriceHistory(d); })
      .catch(err => console.warn('Unable to load cardrush_price_history.json', err));
    return () => { isMounted = false; };
  }, []);

  const enrichedData = useMemo(() => {
    // 1. First pass: extract basic info and build mapping of cardCode -> Set of names
    const codeToNames = new Map();
    const baseData = data.map((item) => {
      const cardCode = getCardCode(item.Picture);
      const seriesCode = getSeriesCode(cardCode);
      const cardId = getCardFilename(item.Picture);
      const imageCode = getImageCode(item.Picture);
      const normalizedName = normalizeCharacter(item.Character);

      if (cardCode && normalizedName) {
        if (!codeToNames.has(cardCode)) {
          codeToNames.set(cardCode, new Set());
        }
        codeToNames.get(cardCode).add(normalizedName);
      }

      const historyEntry = priceHistory[imageCode] || priceHistory[cardCode];
      const confidence = historyEntry ? historyEntry.confidence : undefined;

      return {
        ...item,
        cardCode,
        cardId,
        imageCode,
        seriesCode,
        confidence,
        seriesLabel: formatSeriesLabel(seriesCode),
        normalizedCharacter: normalizedName,
      };
    });

    // 2. Second pass: Build a character name synonym map (DSU-like grouping)
    // If multiple names share the same card code, they are synonyms.
    const nameToCanonical = new Map();
    const nameGroups = []; // List of Sets

    codeToNames.forEach((names) => {
      let targetGroup = null;
      for (const name of names) {
        for (const group of nameGroups) {
          if (group.has(name)) {
            targetGroup = group;
            break;
          }
        }
        if (targetGroup) break;
      }

      if (!targetGroup) {
        targetGroup = new Set();
        nameGroups.push(targetGroup);
      }

      names.forEach(n => targetGroup.add(n));
    });

    // Simplify canonical mapping: prefer Japanese name if multiple exist
    nameGroups.forEach((group) => {
      const namesArray = Array.from(group);
      // Heuristic: Japanese names usually have katakana/hiragana/kanji
      const canonical = namesArray.find(n => /[^\x00-\x7F]/.test(n)) || namesArray[0];
      group.forEach(n => nameToCanonical.set(n, canonical));
    });

    // 3. Final pass: apply canonical names
    return baseData.map(item => ({
      ...item,
      canonicalCharacter: nameToCanonical.get(item.normalizedCharacter) || item.normalizedCharacter
    }));
  }, [data, priceHistory, getImageCode]);

  const wishlistSet = useMemo(() => new Set(wishlist), [wishlist]);
  const cardIdToCharacter = useMemo(() => {
    const map = new Map();
    enrichedData.forEach((item) => {
      if (!map.has(item.cardId)) {
        map.set(item.cardId, item.canonicalCharacter);
      }
    });
    return map;
  }, [enrichedData]);
  const favoriteCharacterCounts = useMemo(() => {
    const counts = new Map();
    wishlist.forEach((cardId) => {
      const character = cardIdToCharacter.get(cardId);
      if (!character) {
        return;
      }
      counts.set(character, (counts.get(character) || 0) + 1);
    });
    return counts;
  }, [wishlist, cardIdToCharacter]);

  // Extract unique values for dropdowns
  const characters = useMemo(() => {
    const chars = new Set(enrichedData.map(item => item.canonicalCharacter));
    return Array.from(chars).sort((a, b) => {
      const countB = favoriteCharacterCounts.get(b) || 0;
      const countA = favoriteCharacterCounts.get(a) || 0;
      if (countB !== countA) {
        return countB - countA;
      }
      return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
    });
  }, [enrichedData, favoriteCharacterCounts]);

  const colors = useMemo(() => {
    const cols = new Set(enrichedData.map(item => item.Color));
    return Array.from(cols).sort();
  }, [enrichedData]);
  const seriesLabels = useMemo(() => {
    const labels = new Set(enrichedData.map(item => item.seriesLabel).filter(Boolean));
    return Array.from(labels).sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));
  }, [enrichedData]);

  // Filter data
  const filteredData = useMemo(() => {
    const seriesSelected = sortBy !== 'character';
    const normalizedQuery = searchQuery.trim().toLowerCase();
    return enrichedData.filter(item => {
      const charMatch = selectedCharacter ? item.canonicalCharacter === selectedCharacter : true;
      const colorMatch = selectedColor ? item.Color === selectedColor : true;
      const wishlistMatch = wishlistOnly ? wishlistSet.has(item.cardId) : true;
      const seriesMatch = seriesSelected ? item.seriesLabel === sortBy : true;
      const characterLabel = item.Character || '';
      const normalizedCharacterLabel = item.normalizedCharacter || '';
      const canonicalLabel = item.canonicalCharacter || '';
      const searchMatch = normalizedQuery
        ? characterLabel.toLowerCase().includes(normalizedQuery)
          || normalizedCharacterLabel.toLowerCase().includes(normalizedQuery)
          || canonicalLabel.toLowerCase().includes(normalizedQuery)
          || item.cardCode.toLowerCase().includes(normalizedQuery)
        : true;
      return charMatch && colorMatch && wishlistMatch && seriesMatch && searchMatch;
    });
  }, [enrichedData, selectedCharacter, selectedColor, wishlistOnly, wishlistSet, sortBy, searchQuery]);

  const sortedData = useMemo(() => {
    const sorted = [...filteredData];
    sorted.sort((a, b) => {
      // 1. Primary: Put all wishlisted cards at the very top
      const wishlistDiff = Number(wishlistSet.has(b.cardId)) - Number(wishlistSet.has(a.cardId));
      if (wishlistDiff !== 0) {
        return wishlistDiff;
      }

      // 2. Secondary: Group by character favorite count (popular characters first in both tiers)
      const favoriteDiff = (favoriteCharacterCounts.get(b.canonicalCharacter) || 0) - (favoriteCharacterCounts.get(a.canonicalCharacter) || 0);
      if (favoriteDiff !== 0) {
        return favoriteDiff;
      }

      // 3. Tertiary: Group by character name to keep cards of the same character together
      const charDiff = a.canonicalCharacter.localeCompare(b.canonicalCharacter, undefined, { numeric: true, sensitivity: 'base' });
      if (charDiff !== 0) {
        return charDiff;
      }

      // 4. Finally, sort by card code for a stable order
      return a.cardCode.localeCompare(b.cardCode, undefined, { numeric: true, sensitivity: 'base' });
    });
    return sorted;
  }, [filteredData, favoriteCharacterCounts, wishlistSet]);

  // Reset page on filter change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedCharacter, selectedColor, wishlistOnly, sortBy, searchQuery]);

  // Pagination logic
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = sortedData.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(sortedData.length / itemsPerPage);

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Generate page numbers to display
  const renderPageNumbers = () => {
    const pageNumbers = [];
    const maxVisiblePages = 5;
    
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    if (startPage > 1) {
        pageNumbers.push(
            <button key={1} onClick={() => handlePageChange(1)} className={currentPage === 1 ? 'active' : ''}>
                1
            </button>
        );
        if (startPage > 2) {
            pageNumbers.push(<span key="dots1" className="pagination-dots">...</span>);
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        pageNumbers.push(
            <button key={i} onClick={() => handlePageChange(i)} className={currentPage === i ? 'active' : ''}>
                {i}
            </button>
        );
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            pageNumbers.push(<span key="dots2" className="pagination-dots">...</span>);
        }
        pageNumbers.push(
            <button key={totalPages} onClick={() => handlePageChange(totalPages)} className={currentPage === totalPages ? 'active' : ''}>
                {totalPages}
            </button>
        );
    }

    return pageNumbers;
  };



  return (
    <div className="card-table-container">
      <div className="filters">
        <div className="filter-group">
          <label htmlFor="search-input">Search:</label>
          <input
            id="search-input"
            type="search"
            placeholder="Search character or code (e.g., ST01-021)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label htmlFor="character-select">Character:</label>
          <select 
            id="character-select" 
            value={selectedCharacter} 
            onChange={(e) => setSelectedCharacter(e.target.value)}
          >
            <option value="">All Characters</option>
            {characters.map(char => (
              <option key={char} value={char}>{char}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="color-select">Color:</label>
          <select 
            id="color-select" 
            value={selectedColor} 
            onChange={(e) => setSelectedColor(e.target.value)}
          >
            <option value="">All Colors</option>
            {colors.map(col => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="sort-select">Sort by:</label>
          <select
            id="sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="character">Character (favorites first)</option>
            {seriesLabels.map((label) => (
              <option key={label} value={label}>{label}</option>
            ))}
          </select>
        </div>

        <div className="filter-group wishlist-filter">
          <label htmlFor="wishlist-only">Wishlist:</label>
          <div className="wishlist-toggle">
            <input
              id="wishlist-only"
              type="checkbox"
              checked={wishlistOnly}
              onChange={(e) => setWishlistOnly(e.target.checked)}
            />
            <span>Only show wishlist ({wishlist.length})</span>
          </div>
        </div>
        
        <button
          className="reset-btn"
          onClick={() => {
            setSelectedCharacter('');
            setSelectedColor('');
            setSearchQuery('');
            setSortBy('character');
            setWishlistOnly(false);
          }}
        >
            Reset All
        </button>
      </div>

      <div className="card-grid-wrapper">
        {currentItems.length > 0 ? (
          <div className="card-grid">
            {currentItems.map((item) => {
              const isWishlisted = wishlistSet.has(item.cardId);
              return (
                <div key={item.cardId} className="card-grid-item">
                  <div 
                    className="card-image-shell"
                    style={{
                      width: '100%',
                      maxWidth: '190px',
                      aspectRatio: '2/3',
                      position: 'relative',
                      backgroundColor: '#1a1d27',
                      borderRadius: '8px',
                      overflow: 'visible'
                    }}
                  >
                    <div className="heart-wrapper">
                      <button
                        className={`wishlist-btn ${isWishlisted ? 'active' : ''}`}
                        onClick={(event) => {
                          event.preventDefault();
                          toggleWishlist(item.cardId);
                        }}
                        aria-pressed={isWishlisted}
                        aria-label={isWishlisted ? 'Remove from wishlist' : 'Add to wishlist'}
                      >
                        {isWishlisted ? '♥' : '♡'}
                      </button>
                    </div>
                    <button
                      type="button"
                      className="card-image-btn"
                      onMouseEnter={() => {
                        // Preload proxied image
                        const img = new Image();
                        img.src = `https://wsrv.nl/?url=${encodeURIComponent(item.Picture.split('?')[0])}&output=webp&default=https://placehold.co/150?text=No+Image`;
                      }}
                      onClick={() => setPriceModal(item)}
                      aria-label={`View price history for ${item.cardCode || item.Character}`}
                      style={{
                        width: '100%',
                        display: 'block',
                        padding: 0,
                        border: 'none',
                        background: 'transparent',
                        cursor: 'pointer'
                      }}
                    >
                      <img
                        src={`https://wsrv.nl/?url=${encodeURIComponent(item.Picture.split('?')[0])}&output=webp&default=https://placehold.co/150?text=No+Image`}
                        alt={item.Character}
                        loading="lazy"
                        referrerPolicy="no-referrer"
                        style={{
                          width: '100%',
                          height: 'auto',
                          display: 'block',
                          borderRadius: '8px',
                          minHeight: '100px'
                        }}
                        onError={(e) => {
                          const currentSrc = e.target.src;
                          if (currentSrc.includes('placehold')) return;

                          const historyEntry = priceHistory[item.imageCode] || priceHistory[item.cardCode];
                          const crFallback = historyEntry?.cardrushImage;
                          const cleanUrl = item.Picture.split('?')[0];
                          const encodedUrl = encodeURIComponent(cleanUrl);

                          // Fallback Chain: Proxy (wsrv.nl) -> Local -> Cardrush -> Proxy (weserv) -> Corsproxy -> Placeholder
                          if (currentSrc.includes('wsrv.nl')) {
                            // Primary proxy failed, try local image
                            e.target.src = `${process.env.PUBLIC_URL}/images/cards/${item.cardId}`;
                          } else if (currentSrc.includes('/images/cards/')) {
                            // Local failed, try Cardrush fallback
                            if (crFallback) {
                              e.target.src = crFallback;
                            } else {
                              e.target.src = `https://images.weserv.nl/?url=${encodedUrl}&output=webp&default=https://placehold.co/150?text=No+Image`;
                            }
                          } else if (currentSrc.includes('images.weserv.nl')) {
                            // Secondary proxy failed, try corsproxy or final placeholder
                            if (crFallback) {
                              e.target.src = crFallback;
                            } else {
                              e.target.src = `https://corsproxy.io/?${encodedUrl}`;
                            }
                          } else {
                            e.target.src = 'https://placehold.co/150?text=No+Image';
                          }
                        }}
                      />
                    </button>                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="no-data">No cards found matching your criteria.</div>
        )}
      </div>

      {sortedData.length > itemsPerPage && (
        <div className="pagination">
            <button 
                onClick={() => handlePageChange(currentPage - 1)} 
                disabled={currentPage === 1}
                className="pagination-btn"
            >
                Prev
            </button>
            <div className="page-numbers">
                {renderPageNumbers()}
            </div>
            <button 
                onClick={() => handlePageChange(currentPage + 1)} 
                disabled={currentPage === totalPages}
                className="pagination-btn"
            >
                Next
            </button>
        </div>
      )}
      
      <div className="pagination-info">
        Showing {indexOfFirstItem + 1}-{Math.min(indexOfLastItem, sortedData.length)} of {sortedData.length} results
      </div>
      <p className="filters-note">
        Series selection uses the card code embedded in the image URL (for example, OP-01 or ST-01).
        Alternate art cards are treated as separate entries in the wishlist.
        The wishlist loads from the published wishlist.json file and can be edited locally and exported as JSON.
        Click any card image to view its Cardrush buying price history.
      </p>

      {priceModal && (
        <PriceModal
          item={priceModal}
          priceHistory={priceHistory}
          onClose={() => setPriceModal(null)}
        />
      )}
    </div>
  );
};

export default CardTable;
