import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import logging
from typing import Dict, List, Optional, Tuple, Union
import json
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'click_trader_log.txt')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_stock_price(symbol: str, max_retries: int = 3) -> float:
    """
    Get the current stock price for a given symbol.
    
    Args:
        symbol (str): The stock symbol to get the price for
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        float: The current stock price
    """
    for attempt in range(max_retries):
        try:
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
            stock = yf.Ticker(symbol)
            # Get the most recent data
            data = stock.history(period='1d')
            if data.empty:
                logger.warning(f"No data found for symbol {symbol}")
                return 0.0
            return float(data['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"Error getting price for {symbol} (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retrying
            else:
                return 0.0

def get_stock_info(symbol: str, max_retries: int = 3) -> Dict:
    """
    Get detailed information about a stock.
    
    Args:
        symbol (str): The stock symbol to get information for
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        Dict: Dictionary containing stock information
    """
    for attempt in range(max_retries):
        try:
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # Extract relevant information
            return {
                'symbol': symbol,
                'name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                'volume': info.get('volume', 0),
                'avg_volume': info.get('averageVolume', 0)
            }
        except Exception as e:
            logger.error(f"Error getting info for {symbol} (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retrying
            else:
                return {
                    'symbol': symbol,
                    'name': '',
                    'sector': '',
                    'industry': '',
                    'market_cap': 0,
                    'pe_ratio': 0,
                    'dividend_yield': 0,
                    'fifty_two_week_high': 0,
                    'fifty_two_week_low': 0,
                    'volume': 0,
                    'avg_volume': 0
                }

def get_asx_stocks() -> List[Dict]:
    """
    Get a list of US stocks with their basic information.
    
    Returns:
        List[Dict]: List of dictionaries containing stock information
    """
    # Sample list of US stocks
    sample_stocks = [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "MSFT", "name": "Microsoft Corporation"},
        {"symbol": "GOOGL", "name": "Alphabet Inc."},
        {"symbol": "AMZN", "name": "Amazon.com Inc."},
        {"symbol": "TSLA", "name": "Tesla Inc."},
        {"symbol": "FB", "name": "Meta Platforms Inc."},
        {"symbol": "NFLX", "name": "Netflix Inc."},
        {"symbol": "NVDA", "name": "NVIDIA Corporation"},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
        {"symbol": "V", "name": "Visa Inc."},
        {"symbol": "WMT", "name": "Walmart Inc."},
        {"symbol": "DIS", "name": "The Walt Disney Company"},
        {"symbol": "PG", "name": "Procter & Gamble Co."},
        {"symbol": "KO", "name": "The Coca-Cola Company"}
    ]
    return sample_stocks

def is_asx_open() -> bool:
    """
    Check if the ASX market is currently open.
    
    Returns:
        bool: True if the market is open, False otherwise
    """
    try:
        # Set timezone to Sydney
        sydney_tz = pytz.timezone('Australia/Sydney')
        current_time = datetime.now(sydney_tz)
        
        # Check if it's a weekday
        if current_time.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
            return False
            
        # Market hours: 10:00 AM - 4:00 PM Sydney time
        market_open = current_time.replace(hour=10, minute=0, second=0, microsecond=0)
        market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= current_time <= market_close
    except Exception as e:
        logger.error(f"Error checking ASX market status: {str(e)}")
        return False
