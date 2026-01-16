import React from 'react';
import './App.css';
import CardTable from './components/CardTable';
import cardData from './data.json';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>One Piece Card Game Index</h1>
        <p>{cardData.length} cards have been loaded</p>
      </header>
      <main>
        <CardTable data={cardData} />
      </main>
    </div>
  );
}

export default App;