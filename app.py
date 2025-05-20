from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from flask_sqlalchemy import SQLAlchemy
import logging
import os
from trading_engine import TradingEngine
from alpaca_trader import AlpacaTrader
from price_utils import get_stock_price, get_asx_stocks
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json
import time
import yfinance as yf

# Load environment variables
load_dotenv()
print("APCA_API_KEY_ID:", os.getenv("APCA_API_KEY_ID"))

# Setup logging to a file
logging.basicConfig(
    filename=os.getenv('LOG_FILE', 'click_trader_log.txt'),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def is_market_open(market='asx'):
    """
    Check if the specified market is currently open.
    """
    if market == 'asx':
        # Get current time in Sydney timezone
        sydney_tz = pytz.timezone('Australia/Sydney')
        current_time = datetime.now(sydney_tz)
        
        # Check if it's a weekday
        if current_time.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
            return False
        
        # ASX trading hours: 10:00 AM - 4:00 PM Sydney time
        market_open = current_time.replace(hour=10, minute=0, second=0, microsecond=0)
        market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= current_time <= market_close
    
    elif market in ['nyse', 'nasdaq']:
        # Get current time in New York timezone
        ny_tz = pytz.timezone('America/New_York')
        current_time = datetime.now(ny_tz)
        
        # Check if it's a weekday
        if current_time.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
            return False
        
        # NYSE/NASDAQ trading hours: 9:30 AM - 4:00 PM Eastern Time
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= current_time <= market_close
    
    return False

def get_market_status(market='asx', user_timezone='Australia/Sydney'):
    """
    Get the current status and trading hours for the specified market.
    """
    try:
        user_tz = pytz.timezone(user_timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        user_tz = pytz.timezone('Australia/Sydney')  # Fallback to Sydney timezone

    if market == 'asx':
        market_tz = pytz.timezone('Australia/Sydney')
        market_open = market_tz.localize(datetime.now().replace(hour=10, minute=0, second=0, microsecond=0))
        market_close = market_tz.localize(datetime.now().replace(hour=16, minute=0, second=0, microsecond=0))
        
        # Convert to user's timezone
        market_open_user = market_open.astimezone(user_tz)
        market_close_user = market_close.astimezone(user_tz)
        
        return {
            'name': 'ASX',
            'is_open': is_market_open('asx'),
            'trading_hours': f"{market_open_user.strftime('%I:%M %p')} - {market_close_user.strftime('%I:%M %p')} {user_tz.zone}",
            'timezone': user_timezone
        }
    elif market in ['nyse', 'nasdaq']:
        market_tz = pytz.timezone('America/New_York')
        market_open = market_tz.localize(datetime.now().replace(hour=9, minute=30, second=0, microsecond=0))
        market_close = market_tz.localize(datetime.now().replace(hour=16, minute=0, second=0, microsecond=0))
        
        # Convert to user's timezone
        market_open_user = market_open.astimezone(user_tz)
        market_close_user = market_close.astimezone(user_tz)
        
        return {
            'name': 'NYSE' if market == 'nyse' else 'NASDAQ',
            'is_open': is_market_open(market),
            'trading_hours': f"{market_open_user.strftime('%I:%M %p')} - {market_close_user.strftime('%I:%M %p')} {user_tz.zone}",
            'timezone': user_timezone
        }
    return None

def get_stocks_for_market(market='asx'):
    """
    Get list of stocks for the specified market.
    """
    if market == 'asx':
        return get_asx_stocks()
    elif market in ['nyse', 'nasdaq']:
        # For NYSE and NASDAQ, we'll use a predefined list of major stocks
        # In a production environment, you would want to fetch this from an API
        if market == 'nyse':
            return [
                {'symbol': 'AAPL', 'name': 'Apple Inc.'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
                {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.'},
                {'symbol': 'V', 'name': 'Visa Inc.'},
                {'symbol': 'WMT', 'name': 'Walmart Inc.'},
                {'symbol': 'JNJ', 'name': 'Johnson & Johnson'},
                {'symbol': 'PG', 'name': 'Procter & Gamble Co.'},
                {'symbol': 'MA', 'name': 'Mastercard Inc.'},
                {'symbol': 'HD', 'name': 'Home Depot Inc.'},
                {'symbol': 'BAC', 'name': 'Bank of America Corp.'}
            ]
        else:  # nasdaq
            return [
                {'symbol': 'AAPL', 'name': 'Apple Inc.'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
                {'symbol': 'AMZN', 'name': 'Amazon.com Inc.'},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'},
                {'symbol': 'META', 'name': 'Meta Platforms Inc.'},
                {'symbol': 'TSLA', 'name': 'Tesla Inc.'},
                {'symbol': 'NVDA', 'name': 'NVIDIA Corporation'},
                {'symbol': 'PYPL', 'name': 'PayPal Holdings Inc.'},
                {'symbol': 'INTC', 'name': 'Intel Corporation'},
                {'symbol': 'CMCSA', 'name': 'Comcast Corporation'}
            ]
    return []

app = Flask(__name__)

# Configure the app
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///click_trader.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

# Initialize extensions
db = SQLAlchemy(app)

# Initialize trading engines
ib_engine = TradingEngine()
alpaca_engine = AlpacaTrader()

# Get the preferred trading platform from environment variable
TRADING_PLATFORM = os.getenv('TRADING_PLATFORM', 'alpaca').lower()  # Default to Alpaca

# Connect to the selected trading platform
if TRADING_PLATFORM == 'ib':
    try:
        if ib_engine.connect():
            logging.info("Successfully connected to Interactive Brokers")
        else:
            logging.error("Failed to connect to Interactive Brokers")
    except Exception as e:
        logging.error(f"Error connecting to Interactive Brokers: {str(e)}")
elif TRADING_PLATFORM == 'alpaca':
    try:
        alpaca_engine = AlpacaTrader()
        alpaca_engine.api_key = os.getenv('ALPACA_API_KEY')
        alpaca_engine.api_secret = os.getenv('ALPACA_SECRET_KEY')
        alpaca_engine.base_url = os.getenv('ENDPOINT', 'https://paper-api.alpaca.markets/v2')
        if alpaca_engine.connect():
            logging.info("Connected to Alpaca")
            print("Successfully logged in to Alpaca!")  # Console message for successful login
        else:
            logging.error("Failed to connect to Alpaca")
    except Exception as e:
        logging.error(f"Error initializing Alpaca: {str(e)}")
        alpaca_engine = None

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    display_name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(128))
    portfolios = db.relationship('UserPortfolio', backref='user', lazy=True)
    
    # Trading preferences
    trading_platform = db.Column(db.String(10), default='alpaca')  # 'alpaca' or 'ib'
    primary_market = db.Column(db.String(10), default='asx')  # 'asx', 'nyse', 'nasdaq'
    timezone = db.Column(db.String(50), default='Australia/Sydney')  # Default to Sydney timezone
    
    # Alpaca credentials
    alpaca_api_key = db.Column(db.String(100))
    alpaca_secret_key = db.Column(db.String(100))
    
    # Interactive Brokers settings
    ib_host = db.Column(db.String(100), default='127.0.0.1')
    ib_port = db.Column(db.Integer, default=7497)
    ib_client_id = db.Column(db.Integer, default=1)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Update UserPortfolio model to include user relationship
class UserPortfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_price = db.Column(db.Float)
    last_updated = db.Column(db.DateTime)

# Create database and tables
with app.app_context():
    # Create tables if they don't exist
    db.create_all()
    logging.info("Database tables checked/created.")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        display_name = request.form.get('display_name')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
            
        user = User(email=email, display_name=display_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Log the user in and redirect to profile setup
        session['user_id'] = user.id
        flash('Registration successful! Please set up your trading profile.', 'success')
        return redirect(url_for('profile'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Successfully logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user = User.query.get(session['user_id'])
    market = user.primary_market if user else 'asx'
    
    if request.method == 'POST':
        stock_symbol = request.form.get('stock_symbol')
        quantity = int(request.form.get('quantity', 0))
        
        if not is_market_open(market):
            flash(f'{get_market_status(market, user.timezone)["name"]} is currently closed. Trading is only available during market hours.', 'warning')
            return redirect(url_for('index'))
        
        try:
            # Get current price
            current_price = get_live_price(stock_symbol)
            if current_price is None:
                flash('Could not fetch current price. Please try again.', 'error')
                return redirect(url_for('index'))
            
            # Execute the trade through the selected platform
            trade_success = False
            if user.trading_platform == 'ib':
                trade_success = ib_engine.place_order(stock_symbol, quantity)
            else:  # alpaca
                trade_success = alpaca_engine.place_order(stock_symbol, quantity)
            
            if trade_success:
                # Add to portfolio database
                portfolio = UserPortfolio(
                    user_id=session['user_id'],
                    symbol=stock_symbol.upper(),
                    quantity=quantity,
                    purchase_price=current_price
                )
                db.session.add(portfolio)
                db.session.commit()
                
                flash(f'Successfully bought {quantity} shares of {stock_symbol} at ${current_price:.2f}!', 'success')
            else:
                flash(f'Failed to execute trade through {user.trading_platform.upper()}.', 'error')
        except Exception as e:
            logging.error(f"Error executing trade: {str(e)}")
            flash('An error occurred while executing the trade.', 'error')
        
        return redirect(url_for('index'))
    
    # Get user's portfolio
    portfolios = UserPortfolio.query.filter_by(user_id=session['user_id']).all()
    portfolio_data = []
    for p in portfolios:
        current_price = get_live_price(p.symbol)
        last_closed_price = get_stock_price(p.symbol, use_last_closed=True)
        price_change = None
        if current_price and p.purchase_price:
            price_change = ((current_price - p.purchase_price) / p.purchase_price) * 100
        
        portfolio_data.append({
            'symbol': p.symbol,
            'quantity': p.quantity,
            'purchase_price': p.purchase_price,
            'current_price': current_price,
            'last_closed_price': last_closed_price,
            'price_change': price_change,
            'purchase_date': p.purchase_date.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    market_status = get_market_status(market, user.timezone)
    return render_template('index.html', 
                         portfolio=portfolio_data,
                         market_status=market_status,
                         stocks=get_stocks_for_market(market),
                         trading_platform=user.trading_platform.upper())

@app.route('/delete/<int:portfolio_id>', methods=['POST'])
@login_required
def delete_stock(portfolio_id):
    portfolio = UserPortfolio.query.get_or_404(portfolio_id)
    if portfolio.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    try:
        # Execute sell order through the selected platform
        trade_success = False
        if portfolio.user.trading_platform == 'ib':
            trade_success = ib_engine.place_order(portfolio.symbol, -portfolio.quantity)
        else:  # alpaca
            trade_success = alpaca_engine.place_order(portfolio.symbol, -portfolio.quantity)
        
        if trade_success:
            db.session.delete(portfolio)
            db.session.commit()
            flash(f'Successfully sold {portfolio.quantity} shares of {portfolio.symbol}!', 'success')
        else:
            flash(f'Failed to execute sell order through {portfolio.user.trading_platform.upper()}.', 'error')
    except Exception as e:
        logging.error(f"Error executing sell order: {str(e)}")
        flash('An error occurred while selling the stock.', 'error')
    
    return redirect(url_for('index'))

@app.route('/price/<symbol>')
def get_price(symbol):
    price = get_stock_price(symbol)
    if price is not None:
        return {'price': price}
    else:
        return {'error': 'Price not found'}, 404

@app.route('/price-check')
@login_required
def price_check():
    stocks = get_asx_stocks()
    stock_data = []
    
    for stock in stocks:
        symbol = stock['symbol']
        # Add .AX suffix for ASX stocks if not already present
        yahoo_symbol = f"{symbol}.AX" if not symbol.endswith('.AX') else symbol
        
        price_info = {
            'symbol': symbol,
            'price': 'Unable to determine price',
            'price_change': 0,
            'source': 'None',
            'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Try Yahoo Finance first
        try:
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period='5d')
            if not hist.empty:
                latest_price = hist['Close'].iloc[-1]
                oldest_price = hist['Close'].iloc[0]
                price_change = ((latest_price - oldest_price) / oldest_price) * 100
                
                price_info['price'] = f"${latest_price:.2f}"
                price_info['price_change'] = price_change
                price_info['source'] = 'Yahoo Finance'
                stock_data.append(price_info)
                continue
        except Exception as e:
            logging.warning(f"Yahoo Finance failed for {yahoo_symbol}: {str(e)}")
        
        # Try Alpaca if Yahoo Finance failed
        if TRADING_PLATFORM == 'alpaca' and alpaca_engine and alpaca_engine.connected:
            try:
                alpaca_symbol = f"{symbol}.AX" if not symbol.endswith('.AX') else symbol
                quote = alpaca_engine.api.get_latest_trade(alpaca_symbol)
                price_info['price'] = f"${float(quote.price):.2f}"
                price_info['source'] = 'Alpaca'
            except Exception as e:
                logging.warning(f"Alpaca failed for {symbol}: {str(e)}")
        
        stock_data.append(price_info)
    
    return render_template('price_check.html', stocks=stock_data)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])
    
    # Get list of common timezones
    common_timezones = [
        ('Australia/Sydney', 'Sydney, Australia'),
        ('Australia/Melbourne', 'Melbourne, Australia'),
        ('Australia/Perth', 'Perth, Australia'),
        ('America/New_York', 'New York, USA'),
        ('America/Chicago', 'Chicago, USA'),
        ('America/Los_Angeles', 'Los Angeles, USA'),
        ('Europe/London', 'London, UK'),
        ('Europe/Paris', 'Paris, France'),
        ('Asia/Tokyo', 'Tokyo, Japan'),
        ('Asia/Singapore', 'Singapore')
    ]
    
    if request.method == 'POST':
        # Update trading platform
        user.trading_platform = request.form.get('trading_platform', 'alpaca')
        user.primary_market = request.form.get('primary_market', 'asx')
        user.timezone = request.form.get('timezone', 'Australia/Sydney')
        
        # Update Alpaca credentials
        user.alpaca_api_key = request.form.get('alpaca_api_key')
        user.alpaca_secret_key = request.form.get('alpaca_secret_key')
        
        # Update IB settings
        user.ib_host = request.form.get('ib_host', '127.0.0.1')
        user.ib_port = int(request.form.get('ib_port', 7497))
        user.ib_client_id = int(request.form.get('ib_client_id', 1))
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('profile.html', user=user, timezones=common_timezones)

# User loader for Flask-Login
@app.before_request
def load_user():
    if 'user_id' in session:
        g.current_user = db.session.get(User, session['user_id'])
    else:
        g.current_user = None

# Make current_user available in templates
@app.context_processor
def inject_user():
    return {'current_user': g.current_user if hasattr(g, 'current_user') else None}

def get_live_price(symbol: str) -> float:
    """
    Get the current stock price using Alpaca if connected, otherwise fall back to Yahoo Finance.
    """
    # Try Alpaca first
    if TRADING_PLATFORM == 'alpaca' and alpaca_engine and alpaca_engine.connected:
        try:
            # Alpaca expects US symbols, but for ASX, use .AX suffix
            alpaca_symbol = f"{symbol}.AX" if not symbol.endswith('.AX') else symbol
            quote = alpaca_engine.api.get_latest_trade(alpaca_symbol)
            return float(quote.price)
        except Exception as e:
            logging.warning(f"Alpaca price fetch failed for {symbol}: {e}. Falling back to Yahoo Finance.")
            print(f"Alpaca price fetch failed for {symbol}: {e}. Falling back to Yahoo Finance.")  # Console message for exception
    # Fallback to Yahoo Finance
    return get_stock_price(symbol)

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
