import os
import hmac
import hashlib
import datetime
import json
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

AMAZON_ACCESS_KEY = os.getenv("AMAZON_ACCESS_KEY", "")
AMAZON_SECRET_KEY = os.getenv("AMAZON_SECRET_KEY", "")
AMAZON_PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG", "")
AMAZON_HOST = "webservices.amazon.co.jp"
AMAZON_REGION = "us-west-2"

# Amazon FBA fee rates (approximate, updated periodically)
FBA_RATE = 0.10          # 10% referral fee (category-dependent)
FBA_FIXED = 500          # Fixed FBA fulfillment fee (JPY)
AMAZON_COMMISSION_RATE = 0.08  # 8% Amazon commission


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key(key, date_stamp, region_name, service_name):
    k_date = sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    k_signing = sign(k_service, "aws4_request")
    return k_signing


def call_paapi(payload: dict) -> dict:
    """Call Amazon PA-API v5 with AWS Signature V4."""
    endpoint = "/paapi5/searchitems"
    service = "ProductAdvertisingAPI"
    content_type = "application/json; charset=utf-8"
    target = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"

    t = datetime.datetime.utcnow()
    amz_date = t.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = t.strftime("%Y%m%d")

    body = json.dumps(payload)

    canonical_headers = (
        f"content-encoding:amz-1.0\n"
        f"content-type:{content_type}\n"
        f"host:{AMAZON_HOST}\n"
        f"x-amz-date:{amz_date}\n"
        f"x-amz-target:{target}\n"
    )
    signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"
    payload_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

    canonical_request = "\n".join([
        "POST", endpoint, "",
        canonical_headers, signed_headers, payload_hash
    ])

    credential_scope = f"{date_stamp}/{AMAZON_REGION}/{service}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amz_date, credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    ])

    signing_key = get_signature_key(AMAZON_SECRET_KEY, date_stamp, AMAZON_REGION, service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    auth_header = (
        f"AWS4-HMAC-SHA256 Credential={AMAZON_ACCESS_KEY}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "content-encoding": "amz-1.0",
        "content-type": content_type,
        "host": AMAZON_HOST,
        "x-amz-date": amz_date,
        "x-amz-target": target,
        "Authorization": auth_header,
    }

    url = f"https://{AMAZON_HOST}{endpoint}"
    response = requests.post(url, headers=headers, data=body, timeout=10)
    response.raise_for_status()
    return response.json()


def calculate_profit(buy_price: int, sell_price: int) -> dict:
    """Calculate profit after Amazon fees."""
    referral_fee = int(sell_price * FBA_RATE)
    commission = int(sell_price * AMAZON_COMMISSION_RATE)
    total_fees = referral_fee + commission + FBA_FIXED
    profit = sell_price - buy_price - total_fees
    roi = (profit / buy_price * 100) if buy_price > 0 else 0
    return {
        "buy_price": buy_price,
        "sell_price": sell_price,
        "referral_fee": referral_fee,
        "commission": commission,
        "fba_fixed": FBA_FIXED,
        "total_fees": total_fees,
        "profit": profit,
        "roi": round(roi, 1),
    }


def parse_items(api_response: dict) -> list:
    items = []
    for item in api_response.get("SearchResult", {}).get("Items", []):
        info = item.get("ItemInfo", {})
        offers = item.get("Offers", {})
        listings = offers.get("Listings", []) if offers else []

        title = info.get("Title", {}).get("DisplayValue", "不明")
        asin = item.get("ASIN", "")
        image_url = ""
        images = item.get("Images", {}).get("Primary", {})
        if images:
            image_url = images.get("Large", images.get("Medium", {})).get("URL", "")

        price = 0
        if listings:
            price_obj = listings[0].get("Price", {})
            price = price_obj.get("Amount", 0)

        detail_url = f"https://www.amazon.co.jp/dp/{asin}"

        items.append({
            "asin": asin,
            "title": title,
            "price": int(price),
            "image_url": image_url,
            "detail_url": detail_url,
        })
    return items


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify({"error": "キーワードを入力してください"}), 400

    if not all([AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG]):
        # Return demo data when API keys are not configured
        demo_items = [
            {
                "asin": "B0DEMO001",
                "title": f"【デモ】{keyword} - サンプル商品 A",
                "price": 3200,
                "image_url": "",
                "detail_url": "#",
            },
            {
                "asin": "B0DEMO002",
                "title": f"【デモ】{keyword} - サンプル商品 B",
                "price": 5800,
                "image_url": "",
                "detail_url": "#",
            },
            {
                "asin": "B0DEMO003",
                "title": f"【デモ】{keyword} - サンプル商品 C",
                "price": 1500,
                "image_url": "",
                "detail_url": "#",
            },
        ]
        return jsonify({"items": demo_items, "demo": True})

    try:
        payload = {
            "Keywords": keyword,
            "Resources": [
                "Images.Primary.Large",
                "Images.Primary.Medium",
                "ItemInfo.Title",
                "Offers.Listings.Price",
            ],
            "PartnerTag": AMAZON_PARTNER_TAG,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.co.jp",
            "ItemCount": 10,
        }
        api_response = call_paapi(payload)
        items = parse_items(api_response)
        return jsonify({"items": items})
    except requests.HTTPError as e:
        return jsonify({"error": f"Amazon APIエラー: {e.response.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500


@app.route("/profit")
def profit():
    try:
        buy_price = int(request.args.get("buy", 0))
        sell_price = int(request.args.get("sell", 0))
    except ValueError:
        return jsonify({"error": "価格は整数で入力してください"}), 400

    if buy_price <= 0 or sell_price <= 0:
        return jsonify({"error": "仕入れ値・売値を正しく入力してください"}), 400

    return jsonify(calculate_profit(buy_price, sell_price))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
