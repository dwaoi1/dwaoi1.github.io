import React, { useState, useMemo, useEffect } from 'react';
import './CardTable.css';

const CardTable = ({ data }) => {
  const [selectedCharacter, setSelectedCharacter] = useState('');
  const [selectedColor, setSelectedColor] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');
  const [wishlistOnly, setWishlistOnly] = useState(false);
  const [wishlist, setWishlist] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 100;
  const wishlistStorageKey = 'opcg-wishlist';

  const getCardCode = (url) => {
    const match = url.match(/\/([A-Z]+\d{2,}-\d{3})/);
    return match ? match[1] : '';
  };

  const getSeriesCode = (cardCode) => (cardCode ? cardCode.split('-')[0] : '');

  const formatSeriesLabel = (seriesCode) => {
    if (!seriesCode) {
      return 'Unknown';
    }
    const match = seriesCode.match(/^([A-Z]+)(\d{2})$/);
    return match ? `${match[1]}-${match[2]}` : seriesCode;
  };

  useEffect(() => {
    const saved = localStorage.getItem(wishlistStorageKey);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          setWishlist(parsed);
        }
      } catch (error) {
        console.warn('Unable to parse wishlist data.', error);
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(wishlistStorageKey, JSON.stringify(wishlist));
  }, [wishlist]);

  const enrichedData = useMemo(() => {
    return data.map((item) => {
      const cardCode = getCardCode(item.Picture);
      const seriesCode = getSeriesCode(cardCode);
      const cardId = cardCode || item.Picture;
      return {
        ...item,
        cardCode,
        cardId,
        seriesCode,
        seriesLabel: formatSeriesLabel(seriesCode),
      };
    });
  }, [data]);

  const wishlistSet = useMemo(() => new Set(wishlist), [wishlist]);

  // Extract unique values for dropdowns
  const characters = useMemo(() => {
    const chars = new Set(enrichedData.map(item => item.Character));
    return Array.from(chars).sort();
  }, [enrichedData]);

  const colors = useMemo(() => {
    const cols = new Set(enrichedData.map(item => item.Color));
    return Array.from(cols).sort();
  }, [enrichedData]);

  // Filter data
  const filteredData = useMemo(() => {
    return enrichedData.filter(item => {
      const charMatch = selectedCharacter ? item.Character === selectedCharacter : true;
      const colorMatch = selectedColor ? item.Color === selectedColor : true;
      const wishlistMatch = wishlistOnly ? wishlistSet.has(item.cardId) : true;
      return charMatch && colorMatch && wishlistMatch;
    });
  }, [enrichedData, selectedCharacter, selectedColor, wishlistOnly, wishlistSet]);

  const sortedData = useMemo(() => {
    const sorted = [...filteredData];
    const direction = sortDirection === 'asc' ? 1 : -1;
    sorted.sort((a, b) => {
      let valueA = '';
      let valueB = '';

      if (sortBy === 'series') {
        valueA = a.seriesLabel;
        valueB = b.seriesLabel;
      } else if (sortBy === 'color') {
        valueA = a.Color;
        valueB = b.Color;
      } else {
        valueA = a.Character;
        valueB = b.Character;
      }

      return valueA.localeCompare(valueB, undefined, { numeric: true, sensitivity: 'base' }) * direction;
    });
    return sorted;
  }, [filteredData, sortBy, sortDirection]);

  // Reset page on filter change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedCharacter, selectedColor, wishlistOnly, sortBy, sortDirection]);

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

  const toggleWishlist = (cardId) => {
    setWishlist((prev) => {
      const isSaved = prev.includes(cardId);
      if (isSaved) {
        return prev.filter((id) => id !== cardId);
      }
      return [...prev, cardId];
    });
  };

  return (
    <div className="card-table-container">
      <div className="filters">
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
            <option value="name">Card Name</option>
            <option value="series">Series (OP-01, PRB-01)</option>
            <option value="color">Color</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="sort-direction">Order:</label>
          <select
            id="sort-direction"
            value={sortDirection}
            onChange={(e) => setSortDirection(e.target.value)}
          >
            <option value="asc">A → Z</option>
            <option value="desc">Z → A</option>
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
            setSortBy('name');
            setSortDirection('asc');
            setWishlistOnly(false);
          }}
        >
            Reset All
        </button>
      </div>

      <div className="card-grid-wrapper">
        {currentItems.length > 0 ? (
          <div className="card-grid">
            {currentItems.map((item, index) => {
              const isWishlisted = wishlistSet.has(item.cardId);
              return (
                <div key={`${item.Picture}-${index}`} className="card-grid-item">
                  <button
                    type="button"
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
                  <a
                    href={item.Picture}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <img
                      src={item.Picture}
                      alt={item.Character}
                      loading="lazy"
                      onError={(e) => {
                        e.target.src = 'https://via.placeholder.com/150?text=No+Image';
                      }}
                    />
                  </a>
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
        Series sorting uses the card code embedded in the image URL (for example, OP-01 or ST-01).
        Alternate art cards that share the same card code will be grouped together in the wishlist and series sort.
      </p>
    </div>
  );
};

export default CardTable;
