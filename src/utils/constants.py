from typing import Dict

# Define financial news topic buckets for rotation
# Each bucket targets a specific market segment to ensure diversity
QUERY_BUCKETS: Dict[str, str] = {
    "macro_economy": "GDP CPI 雇用統計 金融政策 日銀 FRB インフレ デフレ 景気動向",
    "japanese_stock": "日経平均 TOPIX 日本株 決算 上方修正 自社株買い 株式分割 プライム市場 グロース市場",
    "us_stock": "米国株 NYダウ S&P500 NASDAQ GAFA M7 決算 米国経済",
    "forex_rates": "ドル円 為替 円安 円高 金利差 為替介入 FX",
    "commodities": "原油価格 金相場 商品先物 エネルギー価格 天然ガス 穀物相場",
    "crypto_web3": "ビットコイン 暗号資産 仮想通貨 イーサリアム ブロックチェーン Web3 NFT",
    "tech_semicon": "半導体 生成AI 人工知能 テクノロジー DX スタートアップ"
}

# Default fetch settings
DEFAULT_FETCH_COUNT = 50
DEFAULT_FINAL_COUNT = 3
DEFAULT_COOLDOWN_HOURS = 24
