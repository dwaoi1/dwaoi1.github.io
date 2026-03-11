const fs = require('fs');
const path = require('path');

const source = path.resolve(__dirname, '../one_piece_scripts/one_piece_cards.json');
const target = path.resolve(__dirname, 'public/cards.json');

if (fs.existsSync(source)) {
  fs.copyFileSync(source, target);
  console.log(`Copied card data: ${source} -> ${target}`);
} else {
  console.warn(`Card data source not found, keeping existing ${target}: ${source}`);
}

buildPriceData();

function parseAmount(amountStr) {
  if (!amountStr) return null;
  const cleaned = amountStr.replace(/[¥,]/g, '');
  const val = parseFloat(cleaned);
  return isNaN(val) ? null : val;
}

function getCardCode(url) {
  if (!url) return '';
  const match = url.match(/\/([A-Z]+\d{2,}-\d{3})/);
  return match ? match[1] : '';
}

function findJsonFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  const results = [];
  for (const entry of fs.readdirSync(dir)) {
    const full = path.join(dir, entry);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      results.push(...findJsonFiles(full));
    } else if (entry.endsWith('.json')) {
      results.push(full);
    }
  }
  return results;
}

function buildPriceData() {
  const priceDir = path.resolve(__dirname, '../one_piece_scripts/cardrush_buying_prices');
  const priceFiles = findJsonFiles(priceDir).sort();

  if (priceFiles.length === 0) {
    console.warn('No price files found, skipping price history generation');
    return;
  }

  console.log(`Processing ${priceFiles.length} price files...`);

  // Build history keyed by card code, then by date
  const historyByCode = {};
  for (const file of priceFiles) {
    const date = path.basename(file, '.json');
    let entries;
    try {
      entries = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch (err) {
      console.warn(`Failed to parse ${file}: ${err.message}`);
      continue;
    }
    for (const entry of entries) {
      const code = entry.model_number;
      if (!code) continue;
      if (!historyByCode[code]) historyByCode[code] = {};
      if (!historyByCode[code][date]) historyByCode[code][date] = [];
      historyByCode[code][date].push(entry);
    }
  }

  // Compact to min/max price per date
  const priceHistory = {};
  for (const [code, dateMap] of Object.entries(historyByCode)) {
    const history = [];
    for (const [date, entries] of Object.entries(dateMap)) {
      const prices = entries.map(e => parseAmount(e.amount)).filter(p => p !== null);
      if (prices.length === 0) continue;
      history.push({
        date,
        minPrice: Math.min(...prices),
        maxPrice: Math.max(...prices),
        count: entries.length,
      });
    }
    history.sort((a, b) => a.date.localeCompare(b.date));
    if (history.length > 0) {
      priceHistory[code] = { history };
    }
  }

  const historyTarget = path.resolve(__dirname, 'public/price_history.json');
  fs.writeFileSync(historyTarget, JSON.stringify(priceHistory), 'utf8');
  console.log(`Wrote price history to ${historyTarget} (${Object.keys(priceHistory).length} card codes)`);

  // Build unmatched data using the latest price file
  const cardCodes = new Set();
  if (fs.existsSync(target)) {
    try {
      const cards = JSON.parse(fs.readFileSync(target, 'utf8'));
      for (const card of cards) {
        const code = getCardCode(card.Picture);
        if (code) cardCodes.add(code);
      }
    } catch (err) {
      console.warn(`Failed to parse cards.json: ${err.message}`);
    }
  }

  const allPriceCodes = new Set(Object.keys(historyByCode));

  const latestFile = priceFiles[priceFiles.length - 1];
  const latestDate = path.basename(latestFile, '.json');
  const latestEntries = JSON.parse(fs.readFileSync(latestFile, 'utf8'));
  const latestByCode = {};
  for (const entry of latestEntries) {
    if (!latestByCode[entry.model_number]) latestByCode[entry.model_number] = [];
    latestByCode[entry.model_number].push(entry);
  }

  const multiplePrices = Object.entries(latestByCode)
    .filter(([, entries]) => entries.length > 1)
    .map(([code, entries]) => ({ cardCode: code, priceCount: entries.length, entries }));

  const pricesWithoutCards = [...allPriceCodes]
    .filter(code => !cardCodes.has(code))
    .sort()
    .map(code => ({ modelNumber: code, latestEntries: latestByCode[code] || [] }));

  const cardsWithoutPrices = [...cardCodes]
    .filter(code => !allPriceCodes.has(code))
    .sort();

  const unmatchedData = {
    asOf: latestDate,
    multiplePrices,
    pricesWithoutCards,
    cardsWithoutPrices,
  };

  const unmatchedTarget = path.resolve(__dirname, 'public/unmatched_prices.json');
  fs.writeFileSync(unmatchedTarget, JSON.stringify(unmatchedData), 'utf8');
  console.log(`Wrote unmatched data to ${unmatchedTarget}`);
  console.log(`  Multiple prices: ${multiplePrices.length}`);
  console.log(`  Prices without cards: ${pricesWithoutCards.length}`);
  console.log(`  Cards without prices: ${cardsWithoutPrices.length}`);
}
