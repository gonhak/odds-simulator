Odds Simulator – Sports Events & Live Odds Forecasting
A web-based Client-Server application designed to simulate Premier League football matches and dynamically calculate betting odds in real-time. 
The system integrates with a custom naive bayes and decision tree models with an interactive dashboard

# SETUP AND CONFIGURATION

# 1. Clone the repository
git clone https://github.com/your-username/odds-simulator.git
cd odds-simulator

# 2. Database Setup
# Import the schema definition and seed initial Premier League club data into MySQL
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS bookie_db;"
mysql -u root -p bookie_db < database/schema.sql
mysql -u root -p bookie_db < database/seed.sql

# 3. Backend Setup (FastAPI)
cd Backend

# Create and activate a virtual environment
python3.14 -m venv .venv
source .venv/bin/activate

# Install the required dependencies
pip install numpy pandas mysql-connector-python fastapi uvicorn

# Start the Uvicorn development server
uvicorn main:app --reload

# 4. Open the project
