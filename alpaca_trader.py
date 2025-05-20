import alpaca_trade_api as tradeapi
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, time
import pytz

# Load environment variables
load_dotenv()

class AlpacaTrader:
    def __init__(self):
        self.api = None
        self.connected = False
        self.setup_logging()
        self.sydney_tz = pytz.timezone('Australia/Sydney')

    def setup_logging(self):
        self.logger = logging.getLogger('alpaca_trader')
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler('alpaca_trader.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def is_asx_market_open(self):
        """Check if ASX market is currently open"""
        now = datetime.now(self.sydney_tz)
        market_open = time(10, 0)  # 10:00 AM Sydney time
        market_close = time(16, 0)  # 4:00 PM Sydney time
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
            return False
            
        current_time = now.time()
        return market_open <= current_time <= market_close

    def connect(self):
        try:
            # Initialize Alpaca API
            self.api = tradeapi.REST(
                key_id=os.getenv('ALPACA_API_KEY'),
                secret_key=os.getenv('ALPACA_SECRET_KEY'),
                base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'),  # Use paper trading by default
                api_version='v2'
            )
            
            # Test connection by getting account info
            account = self.api.get_account()
            self.connected = True
            self.logger.info(f"Successfully connected to Alpaca. Account status: {account.status}")
            return True
        except Exception as e:
            self.logger.error(f"Connection error: {str(e)}")
            return False

    def place_order(self, symbol, quantity, order_type='market', limit_price=None):
        if not self.connected:
            self.logger.error("Not connected to Alpaca")
            return False

        if not self.is_asx_market_open():
            self.logger.error("ASX market is currently closed")
            return False

        try:
            # Add .AX suffix for ASX stocks
            symbol = f"{symbol}.AX"
            
            # Determine if this is a buy or sell order
            side = 'buy' if quantity > 0 else 'sell'
            quantity = abs(quantity)  # Convert to positive number
            
            # Create order
            if order_type == 'market':
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=quantity,
                    side=side,
                    type='market',
                    time_in_force='day'
                )
            elif order_type == 'limit' and limit_price is not None:
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=quantity,
                    side=side,
                    type='limit',
                    time_in_force='day',
                    limit_price=limit_price
                )
            else:
                self.logger.error(f"Invalid order type or missing limit price: {order_type}")
                return False
            
            self.logger.info(f"Order placed successfully: {side} {quantity} {symbol}")
            return True
        except Exception as e:
            self.logger.error(f"Order placement error: {str(e)}")
            return False

    def get_portfolio_value(self):
        if not self.connected:
            self.logger.error("Not connected to Alpaca")
            return 0.0

        try:
            account = self.api.get_account()
            return float(account.equity)
        except Exception as e:
            self.logger.error(f"Error getting portfolio value: {str(e)}")
            return 0.0

    def get_asx_price(self, symbol):
        """Get real-time price for an ASX stock"""
        if not self.connected:
            self.logger.error("Not connected to Alpaca")
            return None

        try:
            # Add .AX suffix for ASX stocks
            #
            pass
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {str(e)}")
            return None

    def disconnect(self):
        if self.connected:
            self.connected = False
            self.logger.info("Disconnected from Alpaca") 