#!/usr/bin/env python3
"""Merge all ST cardrush mappings into card_price_overrides.json."""
import json

# All mappings collected from subagents
all_new_mappings = {
    # ST01 mappings (from initial script + subagent ST01-006)
    "ST01-001": ["モンキー・D・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/1.webp"],
    "ST01-004": ["サンジ(illust:Koushi Rokushiro)", "https://files.cardrush.media/onepiece/ocha_products/1046.webp"],
    "ST01-005": ["ジンベエ(illust:Yoshiko Umakoshi)", "https://files.cardrush.media/onepiece/ocha_products/2271.webp"],
    "ST01-006": ["トニートニー・チョッパー(白枠/漫画絵)", "https://files.cardrush.media/onepiece/ocha_products/1047.webp"],
    "ST01-006_p1": ["トニートニー・チョッパー(甲冑/漫画背景)", "https://files.cardrush.media/onepiece/ocha_products/952.webp"],
    "ST01-006_p4": ["トニートニー・チョッパー(foil/赤枠/漫画絵)", "https://files.cardrush.media/onepiece/ocha_products/953.webp"],
    "ST01-006_p6": ["トニートニー・チョッパー(角強化/illust:TAPIOCA)", "https://files.cardrush.media/onepiece/ocha_products/1048.webp"],
    "ST01-006_p7": ["トニートニー・チョッパー(illust:Akiko Sugizono)", "https://files.cardrush.media/onepiece/ocha_products/2277.webp"],
    "ST01-006_p9": ["トニートニー・チョッパー(フルアート/foil)", "https://files.cardrush.media/onepiece/ocha_products/4989.webp"],
    "ST01-006_p10": ["トニートニー・チョッパー(パラレル/手に瓶/illust:TAPIOCA)", "https://files.cardrush.media/onepiece/ocha_products/4990.webp"],
    "ST01-007": ["ナミ(白枠/漫画絵)", "https://files.cardrush.media/onepiece/ocha_products/1051.webp"],
    "ST01-008": ["ニコ・ロビン(illust:He Ziwei)", "https://files.cardrush.media/onepiece/ocha_products/2275.webp"],
    "ST01-009": ["ネフェルタリ・ビビ(illust:NAOSHI KOMI)", "https://files.cardrush.media/onepiece/ocha_products/1052.webp"],
    "ST01-011": ["ブルック(illust:Hayaken-sarena)", "https://files.cardrush.media/onepiece/ocha_products/1054.webp"],
    "ST01-012": ["モンキー・D・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/12.webp"],
    "ST01-013": ["ロロノア・ゾロ", "https://files.cardrush.media/onepiece/ocha_products/13.webp"],
    "ST01-015": ["ゴムゴムのJET銃(ノーマル仕様/illust:Makitoshi)", "https://files.cardrush.media/onepiece/ocha_products/1057.webp"],
    "ST01-017": ["サウザンド・サニー号", "https://files.cardrush.media/onepiece/ocha_products/17.webp"],
    
    # ST02 mappings
    "ST02-001": ["ユースタス・キッド", "https://files.cardrush.media/onepiece/ocha_products/18.webp"],
    "ST02-007": ["ジュエリー・ボニー", "https://files.cardrush.media/onepiece/ocha_products/24.webp"],
    "ST02-008": ["スクラッチメン・アプー(illust:DAI-XT.)", "https://files.cardrush.media/onepiece/ocha_products/1060.webp"],
    "ST02-009": ["トラファルガー・ロー", "https://files.cardrush.media/onepiece/ocha_products/26.webp"],
    "ST02-010": ["バジル・ホーキンス(illust:Hayaken-sarena)", "https://files.cardrush.media/onepiece/ocha_products/4177.webp"],
    "ST02-013": ["ユースタス・キッド(TREASURECRUISE)", "https://files.cardrush.media/onepiece/ocha_products/1214.webp"],
    
    # ST03 mappings
    "ST03-001": ["クロコダイル", "https://files.cardrush.media/onepiece/ocha_products/35.webp"],
    "ST03-003": ["クロコダイル(TREASURECRUISE)", "https://files.cardrush.media/onepiece/ocha_products/1215.webp"],
    "ST03-004": ["ゲッコー・モリア(レリーフ仕様/illust:touge369)", "https://files.cardrush.media/onepiece/ocha_products/8585.webp"],
    "ST03-008": ["トラファルガー・ロー(illust:tasaka)", "https://files.cardrush.media/onepiece/ocha_products/1066.webp"],
    "ST03-009": ["ドンキホーテ・ドフラミンゴ", "https://files.cardrush.media/onepiece/ocha_products/43.webp"],
    "ST03-012": ["パシフィスタ(illust:ASAKI KURODA)", "https://files.cardrush.media/onepiece/ocha_products/1270.webp"],
    "ST03-013": ["ボア・ハンコック", "https://files.cardrush.media/onepiece/ocha_products/47.webp"],
    "ST03-014": ["マーシャル・D・ティーチ(illust:DAI-XT.)", "https://files.cardrush.media/onepiece/ocha_products/1067.webp"],
    "ST03-017": ["メロメロ甘風", "https://files.cardrush.media/onepiece/ocha_products/51.webp"],
    
    # ST04 mappings
    "ST04-001": ["カイドウ", "https://files.cardrush.media/onepiece/ocha_products/52.webp"],
    "ST04-002": ["うるティ(illust:otton)", "https://files.cardrush.media/onepiece/ocha_products/6093.webp"],
    "ST04-003": ["カイドウ(TREASURECRUISE)", "https://files.cardrush.media/onepiece/ocha_products/1216.webp"],
    "ST04-005": ["クイーン(illust:Studio Vigor Co.Ltd)", "https://files.cardrush.media/onepiece/ocha_products/1068.webp"],
    "ST04-011": ["ブラックマリア(illust:sohin)", "https://files.cardrush.media/onepiece/ocha_products/1217.webp"],
    "ST04-016": ["熱息(illust:tatsuya)", "https://files.cardrush.media/onepiece/ocha_products/1272.webp"],
    "ST04-017": ["鬼ヶ島(illust:KISUKE)", "https://files.cardrush.media/onepiece/ocha_products/4191.webp"],
    
    # ST05 mappings
    "ST05-001": ["シャンクス", "https://files.cardrush.media/onepiece/ocha_products/69.webp"],
    "ST05-002": ["アイン(illust:Hashimoto Q)", "https://files.cardrush.media/onepiece/ocha_products/6094.webp"],
    "ST05-004": ["ウタ", "https://files.cardrush.media/onepiece/ocha_products/72.webp"],
    
    # ST06 mappings
    "ST06-006_p1": ["たしぎ(フルアート/foil/illust:Nekobayashi)", "https://files.cardrush.media/onepiece/ocha_products/3505.webp"],
    "ST06-006_p2": ["たしぎ(パラレル/SP/和柄/illust:Hashimoto Q)", "https://files.cardrush.media/onepiece/ocha_products/4442.webp"],
    
    # ST07 mappings
    "ST07-010_p2": ["シャーロット・リンリン(未開封/illust:Hatori Kyoka)", "https://files.cardrush.media/onepiece/ocha_products/1075.webp"],
    "ST07-008_p3": ["シャーロット・プリン(illust:hmng)", "https://files.cardrush.media/onepiece/ocha_products/1219.webp"],
    
    # ST08 mappings
    "ST08-002": ["ウタ(illust:sowsow)", "https://files.cardrush.media/onepiece/ocha_products/1220.webp"],
    "ST08-002_p2": ["ウタ", "https://files.cardrush.media/onepiece/ocha_products/121.webp"],
    "ST08-005": ["シャンクス", "https://files.cardrush.media/onepiece/ocha_products/124.webp"],
    "ST08-011": ["モンキー・D・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/130.webp"],
    "ST08-015": ["ゴムゴムの銃", "https://files.cardrush.media/onepiece/ocha_products/134.webp"],
    
    # ST09 mappings
    "ST09-001": ["ヤマト", "https://files.cardrush.media/onepiece/ocha_products/135.webp"],
    "ST09-011": ["モンキー・D・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/145.webp"],
    "ST09-012": ["ヤマト(illust:Takashi Kojima)", "https://files.cardrush.media/onepiece/ocha_products/2269.webp"],
    
    # ST10 mappings
    "ST10-001": ["モンキー・D・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/149.webp"],
    "ST10-002": ["ポートガス・D・エース", "https://files.cardrush.media/onepiece/ocha_products/150.webp"],
    "ST10-003": ["モンキー・D・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/151.webp"],
    "ST10-006": ["ロロノア・ゾロ", "https://files.cardrush.media/onepiece/ocha_products/154.webp"],
    "ST10-008": ["サンジ", "https://files.cardrush.media/onepiece/ocha_products/156.webp"],
    "ST10-010": ["ニコ・ロビン", "https://files.cardrush.media/onepiece/ocha_products/158.webp"],
    "ST10-013": ["ナミ", "https://files.cardrush.media/onepiece/ocha_products/161.webp"],
    "ST10-015": ["ウソップ", "https://files.cardrush.media/onepiece/ocha_products/163.webp"],
    
    # ST11 mappings
    "ST11-001": ["ウタ", "https://files.cardrush.media/onepiece/ocha_products/1194.webp"],
    "ST11-002": ["ウタ", "https://files.cardrush.media/onepiece/ocha_products/1195.webp"],
    "ST11-005": ["私は最強", "https://files.cardrush.media/onepiece/ocha_products/1198.webp"],
    
    # ST12 mappings
    "ST12-001": ["ロロノア・ゾロ＆サンジ", "https://files.cardrush.media/onepiece/ocha_products/1243.webp"],
    "ST12-003": ["ジュラキュール・ミホーク", "https://files.cardrush.media/onepiece/ocha_products/1245.webp"],
    "ST12-009": ["エレファント・ホンマグロ", "https://files.cardrush.media/onepiece/ocha_products/1251.webp"],
    "ST12-010": ["エンポリオ・イワンコフ", "https://files.cardrush.media/onepiece/ocha_products/1252.webp"],
    
    # ST13 mappings
    "ST13-001": ["サボ(カラー版)", "https://files.cardrush.media/onepiece/ocha_products/2723.webp"],
    "ST13-001_p1": ["サボ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/2724.webp"],
    "ST13-001_p2": ["サボ(金文字)", "https://files.cardrush.media/onepiece/ocha_products/6162.webp"],
    "ST13-001_p3": ["サボ(SOUTHEAST ASIAN CHAMPION CHAMPIONSHIP2023/illust:DAI-XT.)", "https://files.cardrush.media/onepiece/ocha_products/6798.webp"],
    "ST13-002": ["ポートガス・D・エース(カラー版)", "https://files.cardrush.media/onepiece/ocha_products/2725.webp"],
    "ST13-002_p1": ["ポートガス・D・エース(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/2726.webp"],
    "ST13-002_p2": ["ポートガス・D・エース(金文字)", "https://files.cardrush.media/onepiece/ocha_products/6163.webp"],
    "ST13-002_p3": ["ポートガス・D・エース(SOUTHEAST ASIAN CHAMPION CHAMPIONSHIP2023/illust:DAI-XT.)", "https://files.cardrush.media/onepiece/ocha_products/6799.webp"],
    "ST13-003": ["モンキー・D・ルフィ(カラー版)", "https://files.cardrush.media/onepiece/ocha_products/2727.webp"],
    "ST13-003_p1": ["モンキー・D・ルフィ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/2728.webp"],
    "ST13-003_p2": ["モンキー・D・ルフィ(金文字)", "https://files.cardrush.media/onepiece/ocha_products/6164.webp"],
    "ST13-003_p3": ["モンキー・D・ルフィ(SOUTHEAST ASIAN CHAMPION CHAMPIONSHIP2023/illust:DAI-XT.)", "https://files.cardrush.media/onepiece/ocha_products/6800.webp"],
    "ST13-011": ["ポートガス・D・エース(カラー版)", "https://files.cardrush.media/onepiece/ocha_products/2743.webp"],
    "ST13-011_p1": ["ポートガス・D・エース(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/2744.webp"],
    "ST13-011_p2": ["ポートガス・D・エース(パラレル/SP/黒背景/illust:otton)", "https://files.cardrush.media/onepiece/ocha_products/8332.webp"],
    "ST13-012_p1": ["マキノ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/2746.webp"],
    "ST13-012_p2": ["マキノ(illust:otton)", "https://files.cardrush.media/onepiece/ocha_products/6095.webp"],
    "ST13-013": ["モンキー・D・ガープ(カラー版)", "https://files.cardrush.media/onepiece/ocha_products/2747.webp"],
    "ST13-013_p1": ["モンキー・D・ガープ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/2748.webp"],
    "ST13-014": ["モンキー・D・ルフィ(ノーマル仕様/カラー版)", "https://files.cardrush.media/onepiece/ocha_products/8763.webp"],
    "ST13-014_p1": ["モンキー・D・ルフィ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/2750.webp"],
    "ST13-014_p2": ["モンキー・D・ルフィ(foil仕様/カラー版)", "https://files.cardrush.media/onepiece/ocha_products/8839.webp"],
    "ST13-015": ["モンキー・D・ルフィ(カラー版)", "https://files.cardrush.media/onepiece/ocha_products/2751.webp"],
    "ST13-015_p1": ["モンキー・D・ルフィ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/2752.webp"],
    "ST13-015_p2": ["モンキー・D・ルフィ(コンパス背景)", "https://files.cardrush.media/onepiece/ocha_products/6662.webp"],
    
    # ST14 mappings
    "ST14-001": ["モンキー・D・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/4053.webp"],
    "ST14-003": ["サンジ", "https://files.cardrush.media/onepiece/ocha_products/4055.webp"],
    "ST14-003_p1": ["サンジ(パラレル/SP/illust:otton)", "https://files.cardrush.media/onepiece/ocha_products/6532.webp"],
    
    # ST15 mappings
    "ST15-002": ["エドワード・ニューゲート(パラレル/★有り/illust:Hokuyuu)", "https://files.cardrush.media/onepiece/ocha_products/8984.webp"],
    "ST15-002_p1": ["エドワード・ニューゲート(パラレル/SP/illust:Bashikou)", "https://files.cardrush.media/onepiece/ocha_products/6523.webp"],
    "ST15-004": ["サッチ", "https://files.cardrush.media/onepiece/ocha_products/4707.webp"],
    "ST15-005": ["ポートガス・D・エース", "https://files.cardrush.media/onepiece/ocha_products/4708.webp"],
    
    # ST16 mappings
    "ST16-001": ["ウタ", "https://files.cardrush.media/onepiece/ocha_products/4717.webp"],
    "ST16-001_p1": ["ウタ(illust:Samei Ikusa)", "https://files.cardrush.media/onepiece/ocha_products/6665.webp"],
    "ST16-001_p2": ["ウタ(パラレル/コンパス背景/illust:Samei Ikusa)", "https://files.cardrush.media/onepiece/ocha_products/6666.webp"],
    "ST16-004": ["シャンクス(★無し)", "https://files.cardrush.media/onepiece/ocha_products/4720.webp"],
    "ST16-004_p1": ["シャンクス(パラレル/SP/タロット柄)", "https://files.cardrush.media/onepiece/ocha_products/7551.webp"],
    "ST16-004_p2": ["シャンクス(パラレル/★有り/illust:Nijihayashi)", "https://files.cardrush.media/onepiece/ocha_products/8985.webp"],
    "ST16-005_p1": ["モンキー・Ｄ・ルフィ(foil仕様)", "https://files.cardrush.media/onepiece/ocha_products/8847.webp"],
    
    # ST17 mappings
    "ST17-002_p1": ["トラファルガー・ロー(パラレル/illust:Morechand)", "https://files.cardrush.media/onepiece/ocha_products/8986.webp"],
    "ST17-003_p3": ["バギー(illust:SHINRA AGENY Co.Ltd.)", "https://files.cardrush.media/onepiece/ocha_products/8567.webp"],
    "ST17-004": ["ボア・ハンコック", "https://files.cardrush.media/onepiece/ocha_products/4728.webp"],
    "ST17-004_p1": ["ボア・ハンコック(illust:Peach Momoko)", "https://files.cardrush.media/onepiece/ocha_products/6667.webp"],
    "ST17-004_p2": ["ボア・ハンコック(パラレル/コンパス背景/illust:Peach Momoko)", "https://files.cardrush.media/onepiece/ocha_products/6668.webp"],
    "ST17-005_p2": ["マーシャル・D・ティーチ(illust:Anderson)", "https://files.cardrush.media/onepiece/ocha_products/8568.webp"],
    
    # ST18 mappings
    "ST18-001": ["ウソ八", "https://files.cardrush.media/onepiece/ocha_products/4733.webp"],
    "ST18-001_p1": ["ウソ八(パラレル/SP/illust:Hashimoto Q)", "https://files.cardrush.media/onepiece/ocha_products/6545.webp"],
    "ST18-001_p2": ["ウソ八(パラレル/illust:Misa Matoki)", "https://files.cardrush.media/onepiece/ocha_products/8987.webp"],
    "ST18-001_p3": ["ウソ八(foil仕様)", "https://files.cardrush.media/onepiece/ocha_products/8850.webp"],
    "ST18-002_p1": ["おナミ(illust:Naruse Uroko)", "https://files.cardrush.media/onepiece/ocha_products/7772.webp"],
    "ST18-002_p2": ["おナミ(foil仕様)", "https://files.cardrush.media/onepiece/ocha_products/8851.webp"],
    "ST18-004": ["ゾロ十郎", "https://files.cardrush.media/onepiece/ocha_products/4736.webp"],
    "ST18-004_p2": ["ゾロ十郎(パラレル/SP/黒背景/illust:Hashimoto Q)", "https://files.cardrush.media/onepiece/ocha_products/8330.webp"],
    "ST18-005": ["ルフィ太郎", "https://files.cardrush.media/onepiece/ocha_products/4737.webp"],
    "ST18-005_p1": ["ルフィ太郎(パラレル/SP/タロット柄)", "https://files.cardrush.media/onepiece/ocha_products/7547.webp"],
    
    # ST19 mappings
    "ST19-002_p1": ["センゴク(illust:Katsuo Tadano)", "https://files.cardrush.media/onepiece/ocha_products/7413.webp"],
    
    # ST20 mappings
    "ST20-001": ["シャーロット・カタクリ", "https://files.cardrush.media/onepiece/ocha_products/4749.webp"],
    "ST20-003": ["シャーロット・ブリュレ(JUDGE)", "https://files.cardrush.media/onepiece/ocha_products/7914.webp"],
    "ST20-005": ["シャーロット・リンリン", "https://files.cardrush.media/onepiece/ocha_products/4753.webp"],
    
    # ST21 mappings
    "ST21-001": ["モンキー・D・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/6753.webp"],
    "ST21-001_p1": ["モンキー・D・ルフィ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/6754.webp"],
    "ST21-001_p2": ["モンキー・D・ルフィ(漫画絵)", "https://files.cardrush.media/onepiece/ocha_products/10819.webp"],
    "ST21-003": ["サンジ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6758.webp"],
    "ST21-003_p1": ["サンジ(foil仕様)", "https://files.cardrush.media/onepiece/ocha_products/8855.webp"],
    "ST21-003_p3": ["サンジ(illust:Koushi Rokushiro)", "https://files.cardrush.media/onepiece/ocha_products/12539.webp"],
    "ST21-004": ["ジュエリー・ボニー(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6760.webp"],
    "ST21-005": ["ジンベエ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6762.webp"],
    "ST21-006": ["ステューシー(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6764.webp"],
    "ST21-007": ["戦桃丸(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6766.webp"],
    "ST21-008": ["トニートニー・チョッパー(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6768.webp"],
    "ST21-009_p1": ["ナミ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6770.webp"],
    "ST21-010_p1": ["ニコ・ロビン(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6772.webp"],
    "ST21-011": ["フランキー(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6774.webp"],
    "ST21-012": ["ブルック(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6776.webp"],
    "ST21-013": ["ベガパンク(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6778.webp"],
    "ST21-014": ["モンキー・D・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/6779.webp"],
    "ST21-014_p1": ["モンキー・D・ルフィ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6780.webp"],
    "ST21-014_p2": ["モンキー・D・ルフィ(ONE PIECE magazine)", "https://files.cardrush.media/onepiece/ocha_products/9852.webp"],
    "ST21-015": ["ロロノア・ゾロ", "https://files.cardrush.media/onepiece/ocha_products/6781.webp"],
    "ST21-015_p1": ["ロロノア・ゾロ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/6782.webp"],
    "ST21-017": ["ゴムゴムのモグラ銃", "https://files.cardrush.media/onepiece/ocha_products/6784.webp"],
    
    # ST22 mappings
    "ST22-001": ["エース&ニューゲート", "https://files.cardrush.media/onepiece/ocha_products/7935.webp"],
    "ST22-001_p1": ["エース&ニューゲート(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7945.webp"],
    "ST22-002": ["イゾウ", "https://files.cardrush.media/onepiece/ocha_products/7936.webp"],
    "ST22-002_p1": ["イゾウ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7946.webp"],
    "ST22-003_p1": ["エドワード・ニューゲート(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7947.webp"],
    "ST22-004_p1": ["エルミー(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7948.webp"],
    "ST22-005_p1": ["光月おでん(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7949.webp"],
    "ST22-006_p1": ["ジョズ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7950.webp"],
    "ST22-007_p1": ["スクアード(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7951.webp"],
    "ST22-008_p1": ["ディカルバン兄弟(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7952.webp"],
    "ST22-009_p1": ["ビスタ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7953.webp"],
    "ST22-010_p1": ["ポートガス・Ｄ・エース(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7954.webp"],
    "ST22-011_p1": ["ホワイティベイ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7970.webp"],
    "ST22-012_p1": ["マルコ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7971.webp"],
    "ST22-013_p1": ["リトルオーズJr.(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7972.webp"],
    "ST22-014_p1": ["Ａ・Ｏ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/7973.webp"],
    "ST22-015": ["おれァ白ひげだァア!!!!", "https://files.cardrush.media/onepiece/ocha_products/7967.webp"],
    
    # ST23 mappings
    "ST23-001": ["ウタ", "https://files.cardrush.media/onepiece/ocha_products/8592.webp"],
    "ST23-002": ["シャンクス", "https://files.cardrush.media/onepiece/ocha_products/8593.webp"],
    
    # ST24 mappings
    "ST24-002": ["キッド＆キラー", "https://files.cardrush.media/onepiece/ocha_products/8602.webp"],
    "ST24-004": ["ロー＆ベポ", "https://files.cardrush.media/onepiece/ocha_products/8604.webp"],
    
    # ST25 mappings
    "ST25-001": ["アルビダ", "https://files.cardrush.media/onepiece/ocha_products/8610.webp"],
    "ST25-003": ["クロコダイル＆ミホーク", "https://files.cardrush.media/onepiece/ocha_products/8612.webp"],
    "ST25-004": ["バギー", "https://files.cardrush.media/onepiece/ocha_products/8613.webp"],
    
    # ST26 mappings
    "ST26-003": ["ニコ・ロビン", "https://files.cardrush.media/onepiece/ocha_products/8620.webp"],
    "ST26-005": ["モンキー・Ｄ・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/8622.webp"],
    "ST26-005_p1": ["モンキー・D・ルフィ(パラレル/SP/悪魔の実模様)", "https://files.cardrush.media/onepiece/ocha_products/12236.webp"],
    
    # ST27 mappings
    "ST27-003": ["クザン", "https://files.cardrush.media/onepiece/ocha_products/8630.webp"],
    "ST27-005": ["マーシャル・Ｄ・ティーチ", "https://files.cardrush.media/onepiece/ocha_products/8632.webp"],
    
    # ST28 mappings
    "ST28-003": ["錦えもん", "https://files.cardrush.media/onepiece/ocha_products/8639.webp"],
    "ST28-005": ["ヤマト", "https://files.cardrush.media/onepiece/ocha_products/8641.webp"],
    
    # ST29 mappings
    "ST29-001": ["モンキー・Ｄ・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/10965.webp"],
    "ST29-001_p1": ["モンキー・Ｄ・ルフィ(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/10982.webp"],
    "ST29-002_p1": ["ウソップ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10983.webp"],
    "ST29-003_p1": ["カク(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10984.webp"],
    "ST29-004": ["サンジ", "https://files.cardrush.media/onepiece/ocha_products/10968.webp"],
    "ST29-004_p1": ["サンジ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10985.webp"],
    "ST29-005_p1": ["ジンベエ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10986.webp"],
    "ST29-006_p1": ["ステューシー(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10987.webp"],
    "ST29-007_p1": ["トニートニー・チョッパー(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10988.webp"],
    "ST29-008_p1": ["ナミ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10989.webp"],
    "ST29-009": ["ニコ・ロビン", "https://files.cardrush.media/onepiece/ocha_products/10973.webp"],
    "ST29-009_p1": ["ニコ・ロビン(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10990.webp"],
    "ST29-010_p1": ["フランキー(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10991.webp"],
    "ST29-011_p1": ["ブルック(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10992.webp"],
    "ST29-012_p1": ["モンキー・Ｄ・ルフィ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10993.webp"],
    "ST29-013_p1": ["ロブ・ルッチ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10994.webp"],
    "ST29-014": ["ロロノア・ゾロ", "https://files.cardrush.media/onepiece/ocha_products/10978.webp"],
    "ST29-014_p1": ["ロロノア・ゾロ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/10995.webp"],
    
    # ST30 mappings
    "ST30-001": ["ルフィ＆エース", "https://files.cardrush.media/onepiece/ocha_products/12796.webp"],
    "ST30-001_p1": ["ルフィ＆エース(パラレル/白黒版)", "https://files.cardrush.media/onepiece/ocha_products/12813.webp"],
    "ST30-002_p1": ["イナズマ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12814.webp"],
    "ST30-003_p1": ["エドワード・ニューゲート(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12815.webp"],
    "ST30-004_p1": ["エンポリオ・イワンコフ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12816.webp"],
    "ST30-005_p1": ["ジョズ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12817.webp"],
    "ST30-006_p1": ["ジンベエ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12818.webp"],
    "ST30-007": ["ポートガス・Ｄ・エース", "https://files.cardrush.media/onepiece/ocha_products/12802.webp"],
    "ST30-007_p1": ["ポートガス・Ｄ・エース(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12819.webp"],
    "ST30-008_p1": ["マルコ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12820.webp"],
    "ST30-009_p1": ["リトルオーズJr.(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12821.webp"],
    "ST30-010_p1": ["クロコダイル(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12822.webp"],
    "ST30-011_p1": ["バギー(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12823.webp"],
    "ST30-012": ["モンキー・D・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/12807.webp"],
    "ST30-012_p1": ["モンキー・D・ルフィ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12824.webp"],
    "ST30-013_p1": ["Mr.2・ボン・クレーベンサム(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12825.webp"],
    "ST30-014": ["Mr.3ギャルディーノ", "https://files.cardrush.media/onepiece/ocha_products/12809.webp"],
    "ST30-014_p1": ["Mr.3ギャルディーノ(パラレル/フルアート)", "https://files.cardrush.media/onepiece/ocha_products/12826.webp"],
    "ST30-015_p1": ["この時代の名が!!!白ひげだァ!!!(★有り/foil)", "https://files.cardrush.media/onepiece/ocha_products/12827.webp"],
    "ST30-016_p1": ["戦えるかルフィ!!!勿論だ!!!(★有り/foil)", "https://files.cardrush.media/onepiece/ocha_products/12828.webp"],
    "ST30-017_p1": ["無茶ばっかりしやがって!!!(★有り/foil)", "https://files.cardrush.media/onepiece/ocha_products/12829.webp"],
    
    # ST31-ST33 mappings (no official images)
    "ST31-001": ["サンジ", "https://files.cardrush.media/onepiece/ocha_products/13910.webp"],
    "ST31-004": ["モンキー・Ｄ・ルフィ", "https://files.cardrush.media/onepiece/ocha_products/13913.webp"],
    "ST31-005": ["サウザンド・サニー号", "https://files.cardrush.media/onepiece/ocha_products/13914.webp"],
    "ST32-002": ["光月おでん", "https://files.cardrush.media/onepiece/ocha_products/13920.webp"],
    "ST32-003": ["ジュラキュール・ミホーク", "https://files.cardrush.media/onepiece/ocha_products/13921.webp"],
    "ST32-005": ["ロロノア・ゾロ", "https://files.cardrush.media/onepiece/ocha_products/13923.webp"],
    "ST33-003": ["スモーカー", "https://files.cardrush.media/onepiece/ocha_products/13930.webp"],
    "ST33-004": ["ボルサリーノ", "https://files.cardrush.media/onepiece/ocha_products/13931.webp"],
    "ST33-005": ["モンキー・Ｄ・ガープ", "https://files.cardrush.media/onepiece/ocha_products/13932.webp"],
}

# Read existing overrides
with open('one_piece_scripts/card_price_overrides.json', 'r', encoding='utf-8') as f:
    overrides = json.load(f)

# Add new mappings
if 'mappings' not in overrides:
    overrides['mappings'] = {}

added_count = 0
updated_count = 0
for key, value in all_new_mappings.items():
    if key in overrides['mappings']:
        updated_count += 1
    else:
        added_count += 1
    overrides['mappings'][key] = value

# Save updated overrides
with open('one_piece_scripts/card_price_overrides.json', 'w', encoding='utf-8') as f:
    json.dump(overrides, f, ensure_ascii=False, indent=2)

print(f"Updated {updated_count} existing mappings")
print(f"Added {added_count} new mappings")
print(f"Total ST mappings: {len([k for k in overrides['mappings'] if k.startswith('ST')])}")
