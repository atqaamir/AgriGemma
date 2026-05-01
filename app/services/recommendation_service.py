"""Recommendation service - generates AI-powered farming recommendations."""
from app.services.ai_model_service import ai_model_service
from app.services.ai_model_service.Gemma.gemma_prompt_service import (
    build_recommendation_prompt,
    build_task_alert_prompt,
)


class RecommendationService:
    """Service for generating farming recommendations using AI."""

    @staticmethod
    def generate_recommendation(weather: dict, soil: dict, crop: dict) -> dict:
        """
        Generate AI-powered farming recommendation.
        
        Args:
            weather: Weather data dict
            soil: Soil data dict
            crop: Crop data dict
            
        Returns:
            dict with recommendation results
        """
        prompt = build_recommendation_prompt(weather, soil, crop)
        
        try:
            response = ai_model_service.complete(prompt)
            return {
                "success": True,
                "recommendation": response,
                "weather": weather,
                "soil": soil,
                "crop": crop,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "recommendation": None,
            }

    @staticmethod
    def generate_task_alerts(weather: dict, soil: dict, crop: dict) -> dict:
        """
        Generate urgent task alerts.
        
        Args:
            weather: Weather data dict
            soil: Soil data dict
            crop: Crop data dict
            
        Returns:
            dict with task alerts
        """
        prompt = build_task_alert_prompt(weather, soil, crop)
        
        try:
            response = ai_model_service.complete(prompt)
            return {
                "success": True,
                "alerts": response,
                "weather": weather,
                "soil": soil,
                "crop": crop,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "alerts": None,
            }