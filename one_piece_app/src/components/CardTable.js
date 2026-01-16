import React, { useState, useMemo } from 'react';
import './CardTable.css';

const CardTable = ({ data }) => {
  const [selectedCharacter, setSelectedCharacter] = useState('');
  const [selectedColor, setSelectedColor] = useState('');

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
                {filteredData.length > 0 ? (
                    filteredData.map((item, index) => (
                        <tr key={index}>
                            <td className="picture-cell">
                                <img 
                                    src={item.Picture} 
                                    alt={item.Character} 
                                    loading="lazy"
                                    onError={(e) => {e.target.src = 'https://via.placeholder.com/150?text=No+Image'}} 
                                />
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
    </div>
  );
};

export default CardTable;
