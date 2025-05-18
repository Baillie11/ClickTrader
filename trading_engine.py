try:
    from quantconnect_api import QuantConnect  # type: ignore
except ImportError:
    print("Warning: quantconnect-api package not found. Some features may not work.")
    QuantConnect = None

from ib_insync import *
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, time
import pytz

# Load environment variables
load_dotenv()

class TradingEngine:
    def __init__(self):
        self.qc = None
        if QuantConnect is not None:
            self.qc = QuantConnect()
        self.ib = IB()
        self.connected = False
        self.setup_logging()
        self.sydney_tz = pytz.timezone('Australia/Sydney')

    def setup_logging(self):
        self.logger = logging.getLogger('trading_engine')
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler('trading_engine.log')
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
            # Connect to Interactive Brokers Australia
            self.ib.connect(
                host=os.getenv('IB_HOST', '127.0.0.1'),
                port=int(os.getenv('IB_PORT', '7497')),  # 7497 for TWS, 7496 for IB Gateway
                clientId=int(os.getenv('IB_CLIENT_ID', '1')),
                readonly=False  # Set to True for paper trading
            )
            
            # Connect to QuantConnect if available
            if self.qc is not None:
                self.qc.connect(
                    os.getenv('QUANTCONNECT_USER_ID'),
                    os.getenv('QUANTCONNECT_API_KEY')
                )
            
            self.connected = True
            self.logger.info("Successfully connected to IB Australia")
            return True
        except Exception as e:
            self.logger.error(f"Connection error: {str(e)}")
            return False

    def place_order(self, symbol, quantity, order_type='MKT', limit_price=None):
        if not self.connected:
            self.logger.error("Not connected to brokers")
            return False

        if not self.is_asx_market_open():
            self.logger.error("ASX market is currently closed")
            return False

        try:
            # Create contract for ASX
            contract = Stock(symbol, 'ASX', 'AUD')
            
            # Create order
            if order_type == 'MKT':
                order = MarketOrder('BUY', quantity)
            elif order_type == 'LMT' and limit_price is not None:
                order = LimitOrder('BUY', quantity, limit_price)
            else:
                self.logger.error(f"Invalid order type or missing limit price: {order_type}")
                return False
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            # Wait for order to fill
            while not trade.isDone():
                self.ib.sleep(0.1)
            
            self.logger.info(f"Order placed successfully: {symbol}, {quantity}")
            return True
        except Exception as e:
            self.logger.error(f"Order placement error: {str(e)}")
            return False

    def get_portfolio_value(self):
        if not self.connected:
            self.logger.error("Not connected to brokers")
            return 0.0

        try:
            account = self.ib.accountSummary()
            for value in account:
                if value.tag == 'NetLiquidation':
                    return float(value.value)
            return 0.0
        except Exception as e:
            self.logger.error(f"Error getting portfolio value: {str(e)}")
            return 0.0

    def get_asx_price(self, symbol):
        """Get real-time price for an ASX stock"""
        if not self.connected:
            self.logger.error("Not connected to brokers")
            return None

        try:
            contract = Stock(symbol, 'ASX', 'AUD')
            self.ib.qualifyContracts(contract)
            ticker = self.ib.reqMktData(contract)
            self.ib.sleep(1)  # Wait for data
            return ticker.marketPrice()
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {str(e)}")
            return None

    def disconnect(self):
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            self.logger.info("Disconnected from brokers") 