import yfinance as yf
import pandas as pd
from price_utils import get_asx_stocks

def fetch_last_closing_prices():
    """
    Fetch the last closing price for all sample US stocks and save them to a CSV file.
    """
    stocks = get_asx_stocks()
    prices = []

    for stock in stocks:
        symbol = stock['symbol']
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d')
            if not hist.empty:
                last_price = hist['Close'].iloc[-1]
                prices.append({'Symbol': symbol, 'Last Closing Price': last_price})
                print(f"{symbol}: {last_price}")
            else:
                print(f"No data found for {symbol}.")
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")

    # Create a DataFrame and save to CSV
    df = pd.DataFrame(prices)
    df.to_csv('last_closing_prices.csv', index=False)
    print("Last closing prices saved to 'last_closing_prices.csv'.")

if __name__ == '__main__':
    fetch_last_closing_prices() 