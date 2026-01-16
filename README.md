# One Piece Card Game Indexer

This is a simple tool to index and display One Piece trading cards.

## How to Update the Website (Step-by-Step)

Follow these steps to add new cards to the website.

### Step 1: Save the Card List
1. Go to the [Official One Piece Card List](https://asia-en.onepiece-cardgame.com/cardlist/).
2. Filter or search for the cards you want to add.
3. Right-click anywhere on the page and select **"Save As..."** (or press `Ctrl + S` / `Cmd + S`).
4. Save the file into the `one_piece_scripts` folder in this project.
   - **Important:** Make sure you save it as **"Webpage, HTML Only"** or **"Webpage, Complete"**. The file should end in `.html`.

### Step 2: Extract the Data
1. Open your **Terminal** (Mac/Linux) or **Command Prompt** (Windows).
2. Navigate to the scripts folder by typing this command and pressing Enter:
   ```bash
   cd one_piece_scripts
   ```
3. Run the extraction script:
   ```bash
   python3 scrape_cards.py
   ```
   - You should see a message saying "Done. Saved X cards to ../one_piece_app/src/data.json".

### Step 3: Update the Website
1. Now that the data is updated, go to the app folder:
   ```bash
   cd ../one_piece_app
   ```
2. Deploy the changes to the internet:
   ```bash
   npm run deploy
   ```
   - This might take a minute. Once it says "Published", you are done!

### Step 4: Save Your Changes (Optional)
If you want to save the history of your changes to GitHub:
```bash
cd ..
git add .
git commit -m "Added new cards"
git push
```

---
**Website Link:** https://dwaoi1.github.io/
