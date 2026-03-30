import React, { useEffect, useState } from 'react';
import './App.css';
import CardTable from './components/CardTable';
import PriceMatching from './components/PriceMatching';
import opcgLogo from './assets/one-piece-card-game-logo.svg';

function App() {
  const [cardData, setCardData] = useState([]);
  const [currentPage, setCurrentPage] = useState('main'); // 'main' or 'matching'

  useEffect(() => {
    let isMounted = true;

    const loadCardData = async () => {
      try {
        const response = await fetch(`${process.env.PUBLIC_URL}/cards.json`, {
          cache: 'no-store',
        });
        if (!response.ok) {
          throw new Error(`Card data request failed: ${response.status}`);
        }
        const data = await response.json();
        if (Array.isArray(data) && isMounted) {
          setCardData(data);
        }
      } catch (error) {
        console.warn('Unable to load cards.json', error);
      }
    };

    loadCardData();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-top">
          <img className="App-logo" src={opcgLogo} alt="One Piece Card Game" />
          <nav className="App-nav">
            <button 
              className={`nav-btn ${currentPage === 'main' ? 'active' : ''}`}
              onClick={() => setCurrentPage('main')}
            >
              Main Page
            </button>
            <button 
              className={`nav-btn ${currentPage === 'matching' ? 'active' : ''}`}
              onClick={() => setCurrentPage('matching')}
            >
              Price Matching
            </button>
          </nav>
        </div>
        <p>{cardData.length} cards have been loaded</p>
      </header>
      <main>
        {currentPage === 'main' ? (
          <CardTable data={cardData} />
        ) : (
          <PriceMatching cardData={cardData} />
        )}
      </main>
    </div>
  );
}

export default App;
