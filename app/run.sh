#!/bin/bash

# Start the python scheduler in the background
python main.py &

# Start the telegram bot in the background
python telegram_bot.py &

# Start the Streamlit application
streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0
