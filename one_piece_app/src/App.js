import React, { useEffect, useState } from 'react';
import './App.css';
import CardTable from './components/CardTable';
import opcgLogo from './assets/one-piece-card-game-logo.svg';

function App() {
  const [cardData, setCardData] = useState([]);

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
        <img className="App-logo" src={opcgLogo} alt="One Piece Card Game" />
        <p>{cardData.length} cards have been loaded</p>
      </header>
      <main>
        <CardTable data={cardData} />
      </main>
    </div>
  );
}

export default App;
