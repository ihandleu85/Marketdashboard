import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize session state for portfolio
if 'holdings' not in st.session_state:
    st.session_state.holdings = {
        'AAPL': {'shares': 10, 'buy_price': 150.00, 'buy_date': '2025-08-01'},
        'GOOGL': {'shares': 5, 'buy_price': 2500.00, 'buy_date': '2025-08-01'},
        'MSFT': {'shares': 8, 'buy_price': 300.00, 'buy_date': '2025-08-01'}
    }

class StockPortfolio:
    def __init__(self):
        self.holdings = st.session_state.holdings

    def add_stock(self, ticker, shares, buy_price, buy_date=None):
        try:
            ticker = ticker.upper().strip()
            shares = int(shares)
            buy_price = float(buy_price)
            if shares <= 0:
                raise ValueError("Number of shares must be positive.")
            if buy_price <= 0:
                raise ValueError("Buy price must be positive.")
            if buy_date is None:
                buy_date = datetime.today().strftime('%Y-%m-%d')
            else:
                datetime.strptime(buy_date, '%Y-%m-%d')
            self.holdings[ticker] = {'shares': shares, 'buy_price': buy_price, 'buy_date': buy_date}
            st.session_state.holdings = self.holdings
            logging.info(f"Added {shares} shares of {ticker} at ${buy_price:.2f} on {buy_date}.")
            return True
        except ValueError as e:
            st.error(f"Error adding stock {ticker}: {e}")
            return False
        except Exception as e:
            st.error(f"Unexpected error adding stock {ticker}: {e}")
            return False

    def remove_stock(self, ticker):
        ticker = ticker.upper().strip()
        if ticker in self.holdings:
            del self.holdings[ticker]
            st.session_state.holdings = self.holdings
            logging.info(f"Removed {ticker} from portfolio.")
            return True
        else:
            st.warning(f"{ticker} not found in portfolio.")
            return False

    @st.cache_data
    def get_current_price(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period='1d')
            if data.empty:
                logging.error(f"No data available for {ticker}.")
                return None
            price = data['Close'].iloc[-1]
            return price
        except Exception as e:
            logging.error(f"Error fetching price for {ticker}: {e}")
            return None

    def calculate_portfolio_value(self):
        data = []
        total_value = 0
        total_profit = 0
        for ticker, info in self.holdings.items():
            current_price = self.get_current_price(ticker)
            if current_price is not None:
                value = info['shares'] * current_price
                profit = (current_price - info['buy_price']) * info['shares']
                total_value += value
                total_profit += profit
                data.append({
                    'Ticker': ticker,
                    'Shares': info['shares'],
                    'Buy Price': info['buy_price'],
                    'Current Price': current_price,
                    'Value': value,
                    'Profit/Loss': profit
                })
        df = pd.DataFrame(data)
        return total_value, total_profit, df

    @st.cache_data
    def generate_signals(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1y')
            if len(hist) < 200:
                logging.warning(f"Insufficient data for {ticker} (need 200 days, got {len(hist)}).")
                return f"Hold (Insufficient data for {ticker})"
            hist['SMA50'] = hist['Close'].rolling(window=50).mean()
            hist['SMA200'] = hist['Close'].rolling(window=200).mean()
            
            sma50_latest = hist['SMA50'].iloc[-1]
            sma200_latest = hist['SMA200'].iloc[-1]
            sma50_prev = hist['SMA50'].iloc[-2]
            sma200_prev = hist['SMA200'].iloc[-2]
            
            if np.isnan(sma50_latest) or np.isnan(sma200_latest):
                logging.warning(f"Invalid SMA data for {ticker}.")
                return f"Hold (Invalid SMA for {ticker})"
            
            if sma50_prev <= sma200_prev and sma50_latest > sma200_latest:
                return f"Buy (Golden Cross) for {ticker}"
            elif sma50_prev >= sma200_prev and sma50_latest < sma200_latest:
                return f"Sell (Death Cross) for {ticker}"
            else:
                return f"Hold for {ticker}"
        except Exception as e:
            logging.error(f"Error generating signal for {ticker}: {e}")
            return f"Hold (Error for {ticker})"

    def check_notifications(self):
        if not self.holdings:
            return ["Portfolio is empty, no notifications to check."]
        notifications = []
        for ticker in self.holdings:
            signal = self.generate_signals(ticker)
            notifications.append(signal)
        return notifications

# Streamlit App
st.title("Stock Portfolio Dashboard")

portfolio = StockPortfolio()

# Add Stock Form
st.subheader("Add New Stock")
with st.form(key="add_stock_form"):
    ticker = st.text_input("Ticker (e.g., AAPL)")
    shares = st.number_input("Shares", min_value=1, step=1)
    buy_price = st.number_input("Buy Price ($)", min_value=0.01, step=0.01)
    submit_button = st.form_submit_button("Add Stock")

if submit_button:
    if portfolio.add_stock(ticker, shares, buy_price):
        st.success(f"Added {shares} shares of {ticker} at ${buy_price:.2f}.")

# Portfolio Summary
st.subheader("Portfolio Summary")
total_value, total_profit, df = portfolio.calculate_portfolio_value()
st.write(f"**Total Portfolio Value**: ${total_value:.2f}")
st.write(f"**Total Profit/Loss**: ${total_profit:.2f}")

# Portfolio Details
st.subheader("Portfolio Details")
if not df.empty:
    st.dataframe(
        df.style.format({
            'Buy Price': '${:.2f}',
            'Current Price': '${:.2f}',
            'Value': '${:.2f}',
            'Profit/Loss': '${:.2f}'
        }).applymap(
            lambda x: 'color: green' if isinstance(x, (int, float)) and x >= 0 else 'color: red',
            subset=['Profit/Loss']
        ),
        use_container_width=True
    )
    # Add Remove Stock Buttons
    for ticker in portfolio.holdings:
        if st.button(f"Remove {ticker}", key=f"remove_{ticker}"):
            portfolio.remove_stock(ticker)
            st.rerun()  # Updated from st.experimental_rerun
else:
    st.write("Portfolio is empty.")

# Notifications
st.subheader("Notifications")
notifications = portfolio.check_notifications()
for note in notifications:
    st.write(f"- {note}")
