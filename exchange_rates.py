"""
ComBank Exchange Rates Scraper API (standalone service)

Scrapes https://www.combank.lk/rates-tariff -> Exchange Rates tab and returns
the buying / selling rates for a given currency (default: US DOLLARS).

Run locally:
    uvicorn exchange_rates:app --host 0.0.0.0 --port 8001 --reload

The exchange rates table is server-rendered into the page HTML, so no browser
(Selenium/Chrome) is needed - a plain HTTPS request + HTML parsing is enough.
"""

import re
import ssl
import logging
import urllib.request
from datetime import datetime, timezone

import certifi
from fastapi import FastAPI, HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ComBank Exchange Rates Scraper", version="1.0.0")

RATES_URL = "https://www.combank.lk/rates-tariff"

# The exchange rates table has 6 numeric columns, in this order.
RATE_COLUMNS = [
    "cheques_buying",
    "cheques_selling",
    "telegraphic_transfers_buying",
    "telegraphic_transfers_selling",
    "buying_rate",            # the plain "Buying Rate" column (currency notes)
    "selling_rate",           # the plain "Selling Rate" column
]

# A currency row: a colspan="2" cell with the currency name, followed by its <td> values.
_ROW_RE = re.compile(
    r'colspan="2"[^>]*>\s*([A-Za-z][A-Za-z .&/()\-]*?)\s*</td>(.*?)</tr>',
    re.IGNORECASE | re.DOTALL,
)
_NUM_RE = re.compile(r'<td[^>]*>\s*([\d,]+\.\d+)\s*</td>')


def fetch_rates_html():
    """Download the rates-tariff page HTML."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(RATES_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        return resp.read().decode("utf-8", "ignore")


def extract_exchange_section(html):
    """Return only the HTML of the Exchange Rates section so we don't pick up
    numbers from other tabs (Interest Rates, Lending Rates, etc.)."""
    start = html.find('id="exchange-rates"')
    if start == -1:
        return html  # fall back to whole page
    # The exchange rates tab ends where the next tab pane begins.
    end = html.find('id="fc-accounts"', start)
    if end == -1:
        # Fall back to the end of the first table in the section
        end = html.find("</table>", start)
        end = end + len("</table>") if end != -1 else len(html)
    return html[start:end]


def parse_all_rates(html):
    """Parse every currency row in the exchange rates section into a dict
    keyed by currency name."""
    section = extract_exchange_section(html)
    rates = {}
    for name, row_html in _ROW_RE.findall(section):
        numbers = _NUM_RE.findall(row_html)
        if len(numbers) < len(RATE_COLUMNS):
            continue  # not a full exchange-rate row
        currency = re.sub(r"\s+", " ", name).strip().upper()
        rates[currency] = dict(zip(RATE_COLUMNS, numbers[:len(RATE_COLUMNS)]))
    return rates


@app.get("/")
def read_root():
    return {
        "message": "ComBank Exchange Rates Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/exchange-rates": "All currencies, or one via ?currency=US DOLLARS",
        },
    }


@app.get("/exchange-rates")
def exchange_rates(currency: str = "US DOLLARS"):
    """Return buying/selling rates. Without a currency it returns USD plus the
    full list of all currencies."""
    try:
        html = fetch_rates_html()
    except Exception as e:
        logger.error(f"Failed to fetch rates page: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch rates page: {str(e)}")

    all_rates = parse_all_rates(html)
    if not all_rates:
        raise HTTPException(status_code=500, detail="Could not parse any exchange rates from the page")

    target = re.sub(r"\s+", " ", currency).strip().upper()
    row = all_rates.get(target)
    if row is None:
        # Try a forgiving match (e.g. "USD" / "US DOLLAR")
        for name, data in all_rates.items():
            if target in name or name in target:
                target, row = name, data
                break

    if row is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Currency '{currency}' not found",
                "available_currencies": sorted(all_rates.keys()),
            },
        )

    return {
        "success": True,
        "source": RATES_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "currency": target,
        "buying_rate": row["buying_rate"],
        "selling_rate": row["selling_rate"],
        "rates": row,                 # full 6-column breakdown
        "all_currencies": all_rates,  # every currency, for convenience
    }
