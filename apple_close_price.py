import yfinance as yf

# Define the ticker symbol
ticker = "AAPL"

# Get data for the stock
stock = yf.Ticker(ticker)

# Get the most recent historical market data
hist = stock.history(period="2d")  # Get last 2 days to ensure we have the last close

# Get the last closing price
last_close = hist['Close'].iloc[-2]  # Second last entry is the last *closed* price
print(f"The last closed price for {ticker} is: ${last_close:.2f}")
