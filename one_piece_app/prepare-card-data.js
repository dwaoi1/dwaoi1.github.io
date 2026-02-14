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
