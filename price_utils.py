import yfinance as yf
import time
from datetime import datetime, timedelta

def get_asx_price(symbol, use_last_closed=False, max_retries=3):
    """
    Get the current or last closed price for an ASX stock.
    
    Args:
        symbol (str): The ASX stock symbol
        use_last_closed (bool): If True, returns the last closed price instead of current price
        max_retries (int): Maximum number of retry attempts
    
    Returns:
        float: The stock price or None if not found
    """
    for attempt in range(max_retries):
        try:
            # Add .AX suffix for ASX stocks
            ticker = yf.Ticker(f"{symbol}.AX")
            
            if use_last_closed:
                # Get the last closed price
                # Use a longer period to ensure we get data
                hist = ticker.history(period="2d")
                if not hist.empty:
                    return float(hist['Close'].iloc[-1])
            else:
                # Get the current price
                info = ticker.info
                if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
                    return float(info['regularMarketPrice'])
                elif 'currentPrice' in info and info['currentPrice'] is not None:
                    return float(info['currentPrice'])
                # If current price not available, try to get the latest close
                hist = ticker.history(period="1d")
                if not hist.empty:
                    return float(hist['Close'].iloc[-1])
            
            # If we get here, we couldn't get a valid price
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait 1 second before retrying
                continue
                
            return None
            
        except Exception as e:
            print(f"Error getting price for {symbol} (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait 1 second before retrying
                continue
            return None 