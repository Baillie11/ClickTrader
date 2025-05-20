import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import json
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from price_utils import get_stock_price, get_stock_info

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

class TradingEngine:
    def __init__(self):
        """Initialize the trading engine with API connections."""
        self.alpaca = None
        self.initialize_apis()
        
    def initialize_apis(self):
        """Initialize trading platform APIs."""
        try:
            # Initialize Alpaca
            self.alpaca = tradeapi.REST(
                os.getenv('ALPACA_API_KEY'),
                os.getenv('ALPACA_API_SECRET'),
                os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
            )
            logger.info("Successfully connected to Alpaca")
        except Exception as e:
            logger.error(f"Error initializing APIs: {str(e)}")
            self.alpaca = None
            
    def get_account_info(self) -> Dict:
        """Get account information from Alpaca."""
        try:
            if self.alpaca:
                account = self.alpaca.get_account()
                return {
                    'cash': float(account.cash),
                    'portfolio_value': float(account.portfolio_value),
                    'buying_power': float(account.buying_power),
                    'equity': float(account.equity),
                    'initial_margin': float(account.initial_margin),
                    'maintenance_margin': float(account.maintenance_margin),
                    'last_equity': float(account.last_equity),
                    'last_maintenance_margin': float(account.last_maintenance_margin),
                    'long_market_value': float(account.long_market_value),
                    'short_market_value': float(account.short_market_value),
                    'status': account.status,
                    'trading_blocked': account.trading_blocked,
                    'transfers_blocked': account.transfers_blocked,
                    'account_blocked': account.account_blocked,
                    'created_at': account.created_at,
                    'trade_suspended_by_user': account.trade_suspended_by_user,
                    'multiplier': account.multiplier,
                    'shorting_enabled': account.shorting_enabled,
                    'pattern_day_trader': account.pattern_day_trader,
                    'day_trade_count': account.day_trade_count,
                    'day_trading_buying_power': float(account.day_trading_buying_power),
                    'regt_buying_power': float(account.regt_buying_power)
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return {}
            
    def get_positions(self) -> List[Dict]:
        """Get current positions from Alpaca."""
        try:
            if self.alpaca:
                positions = self.alpaca.list_positions()
                return [{
                    'symbol': position.symbol,
                    'qty': int(position.qty),
                    'avg_entry_price': float(position.avg_entry_price),
                    'market_value': float(position.market_value),
                    'cost_basis': float(position.cost_basis),
                    'unrealized_pl': float(position.unrealized_pl),
                    'unrealized_plpc': float(position.unrealized_plpc),
                    'current_price': float(position.current_price),
                    'lastday_price': float(position.lastday_price),
                    'change_today': float(position.change_today)
                } for position in positions]
            return []
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return []
            
    def place_order(self, symbol: str, qty: int, side: str, type: str = 'market', time_in_force: str = 'day') -> Dict:
        """Place an order on Alpaca."""
        try:
            if self.alpaca:
                order = self.alpaca.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type=type,
                    time_in_force=time_in_force
                )
                return {
                    'id': order.id,
                    'client_order_id': order.client_order_id,
                    'created_at': order.created_at,
                    'updated_at': order.updated_at,
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at,
                    'expired_at': order.expired_at,
                    'canceled_at': order.canceled_at,
                    'failed_at': order.failed_at,
                    'replaced_at': order.replaced_at,
                    'replaced_by': order.replaced_by,
                    'replaces': order.replaces,
                    'asset_id': order.asset_id,
                    'symbol': order.symbol,
                    'asset_class': order.asset_class,
                    'qty': int(order.qty),
                    'filled_qty': int(order.filled_qty),
                    'type': order.type,
                    'side': order.side,
                    'time_in_force': order.time_in_force,
                    'limit_price': float(order.limit_price) if order.limit_price else None,
                    'stop_price': float(order.stop_price) if order.stop_price else None,
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                    'status': order.status
                }
            return {}
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return {}
            
    def get_orders(self, status: str = 'open') -> List[Dict]:
        """Get orders from Alpaca."""
        try:
            if self.alpaca:
                orders = self.alpaca.list_orders(status=status)
                return [{
                    'id': order.id,
                    'client_order_id': order.client_order_id,
                    'created_at': order.created_at,
                    'updated_at': order.updated_at,
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at,
                    'expired_at': order.expired_at,
                    'canceled_at': order.canceled_at,
                    'failed_at': order.failed_at,
                    'replaced_at': order.replaced_at,
                    'replaced_by': order.replaced_by,
                    'replaces': order.replaces,
                    'asset_id': order.asset_id,
                    'symbol': order.symbol,
                    'asset_class': order.asset_class,
                    'qty': int(order.qty),
                    'filled_qty': int(order.filled_qty),
                    'type': order.type,
                    'side': order.side,
                    'time_in_force': order.time_in_force,
                    'limit_price': float(order.limit_price) if order.limit_price else None,
                    'stop_price': float(order.stop_price) if order.stop_price else None,
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                    'status': order.status
                } for order in orders]
            return []
        except Exception as e:
            logger.error(f"Error getting orders: {str(e)}")
            return []
            
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on Alpaca."""
        try:
            if self.alpaca:
                self.alpaca.cancel_order(order_id)
                return True
            return False
        except Exception as e:
            logger.error(f"Error canceling order: {str(e)}")
            return False 