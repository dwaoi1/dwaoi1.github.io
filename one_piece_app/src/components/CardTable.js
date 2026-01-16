import React, { useState, useMemo, useEffect } from 'react';
import './CardTable.css';

const CardTable = ({ data }) => {
  const [selectedCharacter, setSelectedCharacter] = useState('');
  const [selectedColor, setSelectedColor] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 100;

  // Extract unique values for dropdowns
  const characters = useMemo(() => {
    const chars = new Set(data.map(item => item.Character));
    return Array.from(chars).sort();
  }, [data]);

  const colors = useMemo(() => {
    const cols = new Set(data.map(item => item.Color));
    return Array.from(cols).sort();
  }, [data]);

  // Filter data
  const filteredData = useMemo(() => {
    return data.filter(item => {
      const charMatch = selectedCharacter ? item.Character === selectedCharacter : true;
      const colorMatch = selectedColor ? item.Color === selectedColor : true;
      return charMatch && colorMatch;
    });
  }, [data, selectedCharacter, selectedColor]);

  // Reset page on filter change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedCharacter, selectedColor]);

  // Pagination logic
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = filteredData.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(filteredData.length / itemsPerPage);

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
        
        <button className="reset-btn" onClick={() => {setSelectedCharacter(''); setSelectedColor('')}}>
            Reset Filters
        </button>
      </div>

      <div className="table-wrapper">
        <table className="card-table">
            <thead>
                <tr>
                    <th>Picture</th>
                    <th>Character</th>
                    <th>Color</th>
                </tr>
            </thead>
            <tbody>
                {currentItems.length > 0 ? (
                    currentItems.map((item, index) => (
                        <tr key={index}>
                            <td className="picture-cell">
                                <a href={item.Picture} target="_blank" rel="noopener noreferrer">
                                    <img 
                                        src={item.Picture} 
                                        alt={item.Character} 
                                        loading="lazy"
                                        onError={(e) => {e.target.src = 'https://via.placeholder.com/150?text=No+Image'}} 
                                    />
                                </a>
                            </td>
                            <td>{item.Character}</td>
                            <td>{item.Color}</td>
                        </tr>
                    ))
                ) : (
                    <tr>
                        <td colSpan="3" className="no-data">No cards found matching your criteria.</td>
                    </tr>
                )}
            </tbody>
        </table>
      </div>

      {filteredData.length > itemsPerPage && (
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
        Showing {indexOfFirstItem + 1}-{Math.min(indexOfLastItem, filteredData.length)} of {filteredData.length} results
      </div>
    </div>
  );
};

export default CardTable;