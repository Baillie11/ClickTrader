from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
import os
from trading_engine import TradingEngine
from price_utils import get_asx_price
from datetime import datetime
import pytz

# Setup logging to a file
logging.basicConfig(
    filename='click_trader_log.txt',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def is_asx_open():
    # Get current time in Sydney timezone
    sydney_tz = pytz.timezone('Australia/Sydney')
    sydney_time = datetime.now(sydney_tz)
    
    # Check if it's a weekday
    if sydney_time.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
        return False
    
    # ASX trading hours: 10:00 AM - 4:00 PM Sydney time
    market_open = sydney_time.replace(hour=10, minute=0, second=0, microsecond=0)
    market_close = sydney_time.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= sydney_time <= market_close

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///click_trader.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.urandom(24)  # Required for flash messages
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize trading engine
trading_engine = TradingEngine()

# Define the database model
class UserPortfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_symbol = db.Column(db.String(10), nullable=False)
    investment_amount = db.Column(db.Float, nullable=False)
    trading_type = db.Column(db.String(20), nullable=False)  # e.g., 'simulated', 'real'
    purchase_price = db.Column(db.Float, nullable=True)  # Store the purchase price
    purchase_date = db.Column(db.DateTime, nullable=True)  # Make it nullable initially

# Create database and tables
with app.app_context():
    db.create_all()
    logging.info("Database tables created or verified.")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        stock_symbol = request.form['stock_symbol']
        investment_amount = float(request.form['investment_amount'])
        trading_type = request.form['trading_type']
        
        # Check if ASX is open for real trading
        if trading_type == 'real' and not is_asx_open():
            flash('ASX is currently closed. Your order will be placed when trading resumes.', 'warning')
            return redirect(url_for('index'))
        
        # Get current price for the stock
        current_price = get_asx_price(stock_symbol)
        
        # If real trading is selected, attempt to place the order
        if trading_type == 'real':
            if not trading_engine.connected:
                if not trading_engine.connect():
                    flash('Failed to connect to trading platform. Please try again later.', 'error')
                    return redirect(url_for('index'))
            
            # Calculate quantity based on current price
            quantity = int(investment_amount / current_price) if current_price else 0
            
            if not trading_engine.place_order(stock_symbol, quantity):
                flash('Failed to place order. Please try again later.', 'error')
                return redirect(url_for('index'))
        
        # Add to portfolio database
        portfolio = UserPortfolio(
            stock_symbol=stock_symbol.upper(),
            investment_amount=investment_amount,
            trading_type=trading_type,
            purchase_price=current_price
        )
        db.session.add(portfolio)
        db.session.commit()
        
        flash('Portfolio updated successfully!', 'success')
        logging.info(f"New portfolio added: {stock_symbol}, ${investment_amount}, {trading_type}")
        return redirect(url_for('index'))

    portfolios = UserPortfolio.query.all()
    # Get current prices for all stocks in portfolio
    portfolio_data = []
    for p in portfolios:
        current_price = get_asx_price(p.stock_symbol)
        last_closed_price = get_asx_price(p.stock_symbol, use_last_closed=True)  # Get last closed price
        price_change = None
        if current_price and p.purchase_price:
            price_change = ((current_price - p.purchase_price) / p.purchase_price) * 100
        portfolio_data.append({
            'portfolio': p,
            'current_price': current_price,
            'last_closed_price': last_closed_price,
            'price_change': price_change
        })
    
    # Get ASX status
    asx_status = "Open" if is_asx_open() else "Closed"
    
    return render_template('index.html', portfolios=portfolio_data, asx_status=asx_status)

@app.route('/delete/<int:id>')
def delete(id):
    portfolio = UserPortfolio.query.get_or_404(id)
    db.session.delete(portfolio)
    db.session.commit()
    flash('Portfolio item deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/price/<symbol>')
def get_price(symbol):
    price = get_asx_price(symbol)
    if price is not None:
        return {'price': price}
    else:
        return {'error': 'Price not found'}, 404

if __name__ == '__main__':
    app.run(debug=True)
