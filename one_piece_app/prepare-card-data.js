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

  // Helper: compute min/max/count for a subset of entries
  function priceGroup(subset) {
    const prices = subset.map(e => parseAmount(e.amount)).filter(p => p !== null);
    if (prices.length === 0) return null;
    return { minPrice: Math.min(...prices), maxPrice: Math.max(...prices), count: subset.length };
  }

  // Compact to min/max price per date, with optional sealed/goldText sub-groups
  const priceHistory = {};
  for (const [code, dateMap] of Object.entries(historyByCode)) {
    const history = [];
    for (const [date, entries] of Object.entries(dateMap)) {
      const allPrices = entries.map(e => parseAmount(e.amount)).filter(p => p !== null);
      if (allPrices.length === 0) continue;

      // Classify entries into base / sealed / gold-text-only groups
      const sealedEntries = entries.filter(e => e.name && e.name.includes('未開封'));
      const goldTextEntries = entries.filter(e => e.name && e.name.includes('金文字') && !(e.name.includes('未開封')));
      const baseEntries = entries.filter(e => !(e.name && (e.name.includes('未開封') || e.name.includes('金文字'))));

      const baseGroup = priceGroup(baseEntries);
      const histEntry = baseGroup
        ? { date, minPrice: baseGroup.minPrice, maxPrice: baseGroup.maxPrice, count: baseGroup.count }
        : { date, minPrice: Math.min(...allPrices), maxPrice: Math.max(...allPrices), count: entries.length };

      const sealed = priceGroup(sealedEntries);
      const goldText = priceGroup(goldTextEntries);
      if (sealed) histEntry.sealed = sealed;
      if (goldText) histEntry.goldText = goldText;

      history.push(histEntry);
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

  // Series prefix breakdown helper
  const seriesBreakdown = (codes) => {
    const counts = {};
    for (const code of codes) {
      const m = code.match(/^([A-Z]+\d*)/);
      const prefix = m ? m[1] : (code.includes('-') ? code.split('-')[0] : code);
      counts[prefix] = (counts[prefix] || 0) + 1;
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([series, count]) => ({ series, count }));
  };

  // Name-pattern breakdown for multi-price cards (common keywords in parentheses)
  // "illust:" in card names is the artist credit for CS Championship Series event promos.
  // These are special limited-edition cards signed by a specific illustrator.
  const NAME_PATTERNS = [
    { key: 'パラレル', label: 'Parallel' },
    { key: 'illust', label: 'CS promo (artist credit)' },
    { key: '未開封', label: 'Sealed' },
    { key: '漫画', label: 'Manga art' },
    { key: '金文字', label: 'Gold text' },
    { key: 'CS', label: 'CS event' },
    { key: 'アニメ', label: 'Anime art' },
    { key: 'シリアル', label: 'Serial numbered' },
    { key: 'SP', label: 'SP variant' },
    { key: '開封品', label: 'Opened' },
  ];
  const namePatternCounts = {};
  const namePatternExamples = {};
  for (const { cardCode, entries } of multiplePrices) {
    for (const e of entries) {
      for (const { key, label } of NAME_PATTERNS) {
        if (e.name.includes(key)) {
          namePatternCounts[label] = (namePatternCounts[label] || 0) + 1;
          // Collect up to 3 illustrative examples for the 'CS promo' label
          if (label === 'CS promo (artist credit)' && e.name.includes('illust:')) {
            if (!namePatternExamples[label]) namePatternExamples[label] = [];
            if (namePatternExamples[label].length < 3) {
              const illustMatch = e.name.match(/illust:([^/）)]+)/);
              const artist = illustMatch ? illustMatch[1].trim() : '';
              const entry = `${cardCode} by ${artist}`;
              if (!namePatternExamples[label].includes(entry)) {
                namePatternExamples[label].push(entry);
              }
            }
          }
          break;
        }
      }
    }
  }
  const multiPricePatterns = Object.entries(namePatternCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([pattern, count]) => ({
      pattern,
      count,
      ...(namePatternExamples[pattern] ? { examples: namePatternExamples[pattern] } : {}),
    }));

  // Rarity breakdown for cards without prices (parsed from HTML scraped data)
  const htmlDir = path.resolve(__dirname, '../one_piece_scripts/html_files');
  const codeToRarity = {};
  if (fs.existsSync(htmlDir)) {
    for (const entry of fs.readdirSync(htmlDir)) {
      if (!entry.endsWith('.html')) continue;
      const content = fs.readFileSync(path.join(htmlDir, entry), 'utf8');
      const pattern = /<div class="infoCol">\s*<span>([^<]+)<\/span>\s*\|\s*<span>([^<]+)<\/span>/g;
      let m;
      while ((m = pattern.exec(content)) !== null) {
        const code = m[1].trim();
        const rarity = m[2].trim();
        if (!codeToRarity[code]) codeToRarity[code] = rarity;
      }
    }
  }
  const rarityBreakdown = (codes) => {
    const counts = {};
    for (const code of codes) {
      const rarity = codeToRarity[code] || 'Unknown';
      counts[rarity] = (counts[rarity] || 0) + 1;
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([rarity, count]) => ({ rarity, count }));
  };

  const unmatchedData = {
    asOf: latestDate,
    multiplePrices,
    multiPricePatterns,
    pricesWithoutCards,
    pricesWithoutCardsBreakdown: seriesBreakdown(pricesWithoutCards.map(e => e.modelNumber)),
    cardsWithoutPrices,
    cardsWithoutPricesBreakdown: seriesBreakdown(cardsWithoutPrices),
    cardsWithoutPricesRarityBreakdown: rarityBreakdown(cardsWithoutPrices),
  };

  const unmatchedTarget = path.resolve(__dirname, 'public/unmatched_prices.json');
  fs.writeFileSync(unmatchedTarget, JSON.stringify(unmatchedData), 'utf8');
  console.log(`Wrote unmatched data to ${unmatchedTarget}`);
  console.log(`  Multiple prices (latest day): ${multiplePrices.length}`);
  console.log(`  Prices without cards (all-time codes): ${pricesWithoutCards.length}`);
  console.log(`  Cards without prices (all-time codes): ${cardsWithoutPrices.length}`);
}
