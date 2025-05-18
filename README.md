# ClickTrader

A Flask-based web application for managing ASX stock portfolios with both simulated and real trading capabilities.

## Features

- Real-time ASX stock price tracking
- Portfolio management with purchase prices and current values
- Support for both simulated and real trading
- ASX market hours indicator
- Interactive stock selection with price preview
- Price change tracking and visualization

## Requirements

- Python 3.8+
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- yfinance
- ib_insync (for real trading)
- pytz

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ClickTrader.git
cd ClickTrader
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your settings
```

5. Initialize the database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

6. Run the application:
```bash
python app.py
```

## Usage

1. Open your web browser and navigate to `http://localhost:5000`
2. Select an ASX stock from the dropdown menu
3. Enter your investment amount
4. Choose between simulated or real trading
5. Click "Add" to add the stock to your portfolio

## Trading Hours

The ASX is open Monday to Friday, 10:00 AM - 4:00 PM Sydney time. Real trading orders will be placed when the market is open.

## Deployment

### PythonAnywhere Deployment

1. Create a PythonAnywhere account at https://www.pythonanywhere.com/

2. In the PythonAnywhere dashboard:
   - Go to the "Web" tab
   - Click "Add a new web app"
   - Choose "Manual configuration"
   - Select Python 3.8 or higher

3. Set up your virtual environment:
```bash
cd ~/ClickTrader
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. Configure your web app:
   - Set the working directory to your project directory
   - Set the WSGI configuration file to point to your wsgi.py
   - Add your environment variables in the "Environment variables" section

5. Set up the database:
```bash
flask db upgrade
```

6. Reload your web app

## License

MIT License 