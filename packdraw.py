import requests
import time
import json
from flask import Flask, jsonify, render_template
from datetime import datetime, timedelta
import os
import threading
from flask_cors import CORS
import pytz

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# PackDraw.com API key
api_key = "8cbb2008-f672-454b-907d-aebab8a81485"  # PackDraw.com API key

# Base URL for PackDraw.com API with placeholders for startTime and endTime
url_template = "https://packdraw.com/api/v1/affiliates/leaderboard?after={start_time}&before={end_time}&apiKey={api_key}"

# Timezone configuration
eastern = pytz.timezone("US/Eastern")

# Define start_time and end_time with Eastern time zone
start_time = datetime(2024, 11, 1, 0, 0, 0, tzinfo=eastern).isoformat()  # November 1, 2024
end_date = datetime(2024, 12, 25, 23, 59, 59, tzinfo=eastern).isoformat()  # December 25, 2024

# Data cache for storing fetched data
data_cache = {}

# Function to log detailed output
def log_message(level, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{level.upper()}]: {message}"
    separator = "-" * len(formatted_message)
    print(f"\n{separator}\n{formatted_message}\n{separator}\n")

# Function to fetch data from PackDraw.com API
def fetch_data():
    global data_cache
    try:
        log_message('info', 'Starting data fetch from PackDraw.com API')

        # Set end_time dynamically to current time minus 15 seconds, in Eastern time zone
        end_time = datetime.now(tz=eastern) - timedelta(seconds=15)
        end_time_str = end_time.isoformat()
        log_message('debug', f"Using start_time: {start_time} and end_time: {end_time_str}")

        # Format the API URL with dynamic time parameters
        url = url_template.format(start_time=start_time, end_time=end_time_str, api_key=api_key)
        log_message('debug', f"Fetching from URL: {url}")

        # Fetch the data from PackDraw.com API
        response = requests.get(url)
        log_message('debug', f"Received status code: {response.status_code}")

        if response.status_code == 200:
            # Parse the API response
            api_response = response.json()
            log_message('info', f"Raw API response: {json.dumps(api_response, indent=2)}")

            if isinstance(api_response, dict) and 'leaderboard' in api_response:
                # Extract leaderboard data
                leaderboard_data = api_response['leaderboard']
                data_cache = leaderboard_data  # Cache the leaderboard API data
                log_message('info', 'Data successfully fetched and cached.')
                update_placeholder_data()  # Process the data and update placeholders
            else:
                log_message('warning', 'Invalid data structure in API response.')
                data_cache = {"error": "Invalid data structure in API response."}
        else:
            log_message('error', f"Failed to fetch data. Status code: {response.status_code}")
            log_message('error', f"Response content: {response.text}")

    except Exception as e:
        log_message('error', f"Exception occurred during data fetch: {e}")
        data_cache = {"error": str(e)}

# Function to update the placeholder data with real API data
def update_placeholder_data():
    global data_cache
    try:
        if isinstance(data_cache, list):
            # Sort the data by wagerAmount in descending order
            sorted_data = sorted(data_cache, key=lambda x: x['wagerAmount'], reverse=True)

            # Replace placeholder data with the top wagerers
            top_wagerers = {}
            for i in range(min(11, len(sorted_data))):  # Get up to the top 11 players
                top_wagerers[f'top{i+1}'] = {
                    'username': sorted_data[i]['username'],  # Fetch the username field
                    'wager': f"${sorted_data[i]['wagerAmount']:,.2f}"  # Format wagerAmount with commas and two decimal places
                }

            # Update the global data_cache with the top wagerers
            data_cache = top_wagerers
            log_message('info', f"Top wagerers data updated: {json.dumps(top_wagerers, indent=2)}")
        else:
            log_message('warning', 'No valid data structure found in the API response.')
    except KeyError as e:
        log_message('error', f"KeyError during data update: {e}")
    except Exception as e:
        log_message('error', f"An error occurred while updating placeholder data: {e}")

# Schedule data fetching every 5 minutes
def schedule_data_fetch():
    log_message('info', 'Fetching data every 1.5 minutes.')
    fetch_data()  # Fetch data immediately when the script starts
    threading.Timer(90, schedule_data_fetch).start()  # Schedule the next fetch in 1.5 minutes

# Flask route to serve the cached data
@app.route("/data")
def get_data():
    log_message('info', 'Serving cached data to a client')
    return jsonify(data_cache)

# Route to serve the index.html template
@app.route("/")
def serve_index():
    log_message('info', 'Serving index.html')
    return render_template('index.html')

# Route for handling 404 errors (non-existent pages)
@app.errorhandler(404)
def page_not_found(e):
    log_message('warning', '404 error: Page not found.')
    return render_template('404.html'), 404

# Start the data fetching thread
schedule_data_fetch()

# Run the Flask app on port 8080 (use environment variable for the port)
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))  # Default to port 8080
    log_message('info', f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port)
