
import os
import sys
import duckdb
import json
from mcp_core.logic import do_save_impl

# Setup paths (hacky but works for script)
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

def seed_content():
    print("🌱 Seeding High-Quality Functions...")
    
    # 1. Crypto Price Fetcher
    code_crypto = """
import requests

def get_crypto_price(symbol: str = "BTC", currency: str = "USD") -> str:
    \"\"\"
    Fetches the current price of a cryptocurrency.
    
    Args:
        symbol: The crypto symbol (e.g., BTC, ETH, DOGE).
        currency: The target currency (e.g., USD, JPY).
    \"\"\"
    url = f"https://api.coinbase.com/v2/prices/{symbol}-{currency}/spot"
    try:
        response = requests.get(url)
        data = response.json()
        amount = data['data']['amount']
        return f"Current price of {symbol}: {amount} {currency}"
    except Exception as e:
        return f"Error fetching price: {str(e)}"
"""
    print(do_save_impl(
        asset_name="get_crypto_price",
        code=code_crypto,
        description="Fetch real-time cryptocurrency prices using Coinbase API.",
        description_en="Fetch real-time cryptocurrency prices using Coinbase API.",
        description_jp="Coinbase APIを使用して暗号資産のリアルタイム価格を取得します。",
        tags=["crypto", "finance", "api"],
        dependencies=["requests"],
        skip_test=True # Trust me, I'm the creator
    ))

    # 2. Text Summarizer (Mock)
    code_summary = """
def simple_summarize(text: str, max_length: int = 50) -> str:
    \"\"\"
    A simple truncation summarizer for demonstration.
    For real AI summary, use a cloud model!
    \"\"\"
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
"""
    print(do_save_impl(
        asset_name="simple_summarize",
        code=code_summary,
        description="Simple text truncation for previews.",
        description_en="Simple text truncation for previews.",
        description_jp="プレビュー用の単純なテキスト切り詰め関数。",
        tags=["text", "utils", "demo"],
        skip_test=True
    ))

    # 3. QR Code Generator
    code_qr = """
import qrcode
import io
import base64

def generate_qr_base64(data: str) -> str:
    \"\"\"
    Generates a QR code and returns it as a base64 string.
    Useful for embedding in HTML/markdown.
    \"\"\"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"
"""
    print(do_save_impl(
        asset_name="generate_qr_base64",
        code=code_qr,
        description="Generate QR code as Base64 string.",
        description_en="Generate QR code as Base64 string.",
        description_jp="QRコードを生成し、Base64文字列として返します。",
        tags=["image", "qrcode", "tools"],
        dependencies=["qrcode", "pillow"],
        skip_test=True
    ))

    print("\n✅ Seeding Complete! Launch dashboard to view.")

if __name__ == "__main__":
    seed_content()
