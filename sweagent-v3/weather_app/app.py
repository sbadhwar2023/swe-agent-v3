from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# You should sign up for a free API key at OpenWeatherMap and replace this
API_KEY = "your_api_key_here"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

@app.route("/", methods=["GET", "POST"])
def index():
    weather_data = None
    error = None
    
    if request.method == "POST":
        city = request.form.get("city")
        if city:
            try:
                params = {
                    "q": city,
                    "appid": API_KEY,
                    "units": "metric"  # Use metric units
                }
                response = requests.get(BASE_URL, params=params)
                response.raise_for_status()
                weather_data = response.json()
            except requests.RequestException as e:
                error = f"Error fetching weather data: {str(e)}"
    
    return render_template("index.html", weather_data=weather_data, error=error)

if __name__ == "__main__":
    app.run(debug=True)