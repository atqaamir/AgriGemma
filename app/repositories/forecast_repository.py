from app.models.weather_forecast import WeatherForecast
from app.extensions import db

class CurrentWeatherRepository:
    @staticmethod
    def save_forecast(region, daily_data):
        # Save daily forecast to DB
        for day in daily_data:
            forecast = WeatherForecast(
                region=region,
                date=day['date'],
                temperature_c=day['temperature_c'],
                precipitation_mm=day['precipitation_mm'],
                wind_speed_kph=day['wind_speed_kph']
            )
            db.session.add(forecast)
        db.session.commit()
    


    def get_latest_daily(region, date):
        # Query latest daily forecast from DB
        return WeatherForecast.query.filter_by(region=region, date=date).first()
    
    def get_latest_weekly(region, n=7):
        # Query latest weekly forecast from DB
        return WeatherForecast.query.filter_by(region=region).order_by(WeatherForecast.date.desc()).limit(n).all()
