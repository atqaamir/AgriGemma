"""
Farming Knowledge Base - Rules and best practices for agricultural guidance.
This service provides structured farming knowledge that the chatbot can use
to provide informed recommendations.
"""


class FarmingKnowledgeBase:
    """Centralized farming knowledge for chatbot context."""

    # Irrigation guidelines
    IRRIGATION_RULES = {
        "corn": {
            "critical_moisture": 30,  # %
            "optimal_moisture": 50,
            "warning_moisture": 35,
            "frequency_days": 3,
            "description": "Corn requires consistent moisture during growing season",
        },
        "wheat": {
            "critical_moisture": 25,
            "optimal_moisture": 45,
            "warning_moisture": 30,
            "frequency_days": 5,
            "description": "Wheat is drought-tolerant but needs water during grain fill",
        },
        "soybeans": {
            "critical_moisture": 28,
            "optimal_moisture": 48,
            "warning_moisture": 32,
            "frequency_days": 4,
            "description": "Soybeans are sensitive to water stress during pod development",
        },
        "rice": {
            "critical_moisture": 40,
            "optimal_moisture": 60,
            "warning_moisture": 45,
            "frequency_days": 2,
            "description": "Rice requires flooded conditions during growing season",
        },
    }

    # Disease management
    DISEASE_RULES = {
        "corn_leaf_blight": {
            "symptoms": "Brown lesions on leaves, yellowing",
            "conditions": "Warm, wet weather",
            "prevention": "Use resistant varieties, crop rotation",
            "treatment": "Fungicide application, remove infected leaves",
            "critical_temp_min": 15,
            "critical_temp_max": 30,
            "critical_humidity": 85,
        },
        "powdery_mildew": {
            "symptoms": "White powder-like coating on leaves",
            "conditions": "Dry weather with cool nights",
            "prevention": "Improve air circulation, choose resistant varieties",
            "treatment": "Sulfur spray, neem oil",
            "critical_temp_min": 5,
            "critical_temp_max": 27,
            "critical_humidity": 60,
        },
        "root_rot": {
            "symptoms": "Wilting, yellowing, stunted growth",
            "conditions": "Waterlogged soil, poor drainage",
            "prevention": "Improve drainage, crop rotation, avoid overwatering",
            "treatment": "Reduce irrigation, fungicide treatment",
            "critical_moisture": 70,
        },
    }

    # Planting guidelines
    PLANTING_RULES = {
        "corn": {
            "soil_temp_min": 10,
            "soil_temp_ideal": 15,
            "spacing_inches": 30,
            "depth_inches": 2,
            "season": "Spring",
            "duration_days": 110,
            "description": "Plant after last frost, when soil warms up",
        },
        "wheat": {
            "soil_temp_min": 5,
            "soil_temp_ideal": 15,
            "spacing_inches": 6,
            "depth_inches": 1.5,
            "season": "Fall/Winter",
            "duration_days": 180,
            "description": "Winter variety for fall planting",
        },
        "soybeans": {
            "soil_temp_min": 10,
            "soil_temp_ideal": 20,
            "spacing_inches": 20,
            "depth_inches": 1.5,
            "season": "Spring",
            "duration_days": 100,
            "description": "Plant after corn, soil must be warm",
        },
    }

    # Fertilization guidelines
    FERTILIZATION_RULES = {
        "corn": {
            "nitrogen_lbs_per_acre": 150,
            "phosphorus_lbs_per_acre": 50,
            "potassium_lbs_per_acre": 40,
            "timing": "Pre-plant and side-dress at V6 stage",
            "description": "High nitrogen crop, critical for yield",
        },
        "wheat": {
            "nitrogen_lbs_per_acre": 100,
            "phosphorus_lbs_per_acre": 40,
            "potassium_lbs_per_acre": 30,
            "timing": "Fall and spring applications",
            "description": "Moderate fertilizer needs",
        },
        "soybeans": {
            "nitrogen_lbs_per_acre": 20,
            "phosphorus_lbs_per_acre": 40,
            "potassium_lbs_per_acre": 30,
            "timing": "Pre-plant, relies on nitrogen fixation",
            "description": "Fix own nitrogen, light application sufficient",
        },
    }

    # Pest management
    PEST_RULES = {
        "armyworm": {
            "crops": ["corn", "wheat"],
            "damage": "Leaf damage, defoliation",
            "conditions": "Warm weather, high humidity",
            "prevention": "Monitor regularly, remove weeds",
            "treatment": "Insecticide spray, Bt treatment",
        },
        "aphids": {
            "crops": ["wheat", "soybeans"],
            "damage": "Leaf curling, yellowing, virus transmission",
            "conditions": "Cool season, high humidity",
            "prevention": "Use resistant varieties",
            "treatment": "Insecticidal soap, neem oil",
        },
        "spider_mites": {
            "crops": ["soybeans"],
            "damage": "Yellow stippling on leaves",
            "conditions": "Hot, dry weather",
            "prevention": "Maintain moisture, avoid dust",
            "treatment": "Miticide spray, increase humidity",
        },
    }

    # Weather-based recommendations
    WEATHER_RULES = {
        "heavy_rain": {
            "risk": "Soil erosion, waterlogging, fungal diseases",
            "actions": [
                "Check field drainage",
                "Monitor for root rot",
                "Apply fungicide preventatively",
                "Adjust irrigation schedules",
            ],
        },
        "drought": {
            "risk": "Crop stress, reduced yield, pest susceptibility",
            "actions": [
                "Increase irrigation frequency",
                "Monitor soil moisture closely",
                "Apply deficit irrigation to priority areas",
                "Scout for pest populations",
            ],
        },
        "frost": {
            "risk": "Crop death, delayed planting",
            "actions": [
                "Delay planting if late frost expected",
                "Protect young plants with row covers",
                "Monitor weather forecast",
            ],
        },
        "heatwave": {
            "risk": "Heat stress, reduced pollination, increased water demand",
            "actions": [
                "Increase irrigation",
                "Monitor for insect populations",
                "Ensure proper nutrient availability",
            ],
        },
    }

    @classmethod
    def get_irrigation_rules(cls, crop: str) -> dict:
        """Get irrigation rules for a specific crop."""
        return cls.IRRIGATION_RULES.get(crop.lower(), {})

    @classmethod
    def get_disease_info(cls, disease: str) -> dict:
        """Get information about a specific disease."""
        return cls.DISEASE_RULES.get(disease.lower(), {})

    @classmethod
    def get_planting_guidelines(cls, crop: str) -> dict:
        """Get planting guidelines for a crop."""
        return cls.PLANTING_RULES.get(crop.lower(), {})

    @classmethod
    def get_fertilization_guidelines(cls, crop: str) -> dict:
        """Get fertilization guidelines for a crop."""
        return cls.FERTILIZATION_RULES.get(crop.lower(), {})

    @classmethod
    def get_all_crops(cls) -> list:
        """Get all crops in knowledge base."""
        return list(set(
            list(cls.IRRIGATION_RULES.keys()) +
            list(cls.PLANTING_RULES.keys()) +
            list(cls.FERTILIZATION_RULES.keys())
        ))

    @classmethod
    def to_prompt_context(cls) -> str:
        """Convert knowledge base to text for AI prompt."""
        return f"""
You are an expert agricultural advisor. Use this knowledge base to provide farming guidance:

IRRIGATION GUIDELINES:
{cls._format_dict(cls.IRRIGATION_RULES)}

DISEASE MANAGEMENT:
{cls._format_dict(cls.DISEASE_RULES)}

PLANTING GUIDELINES:
{cls._format_dict(cls.PLANTING_RULES)}

FERTILIZATION GUIDELINES:
{cls._format_dict(cls.FERTILIZATION_RULES)}

PEST MANAGEMENT:
{cls._format_dict(cls.PEST_RULES)}

WEATHER-BASED RECOMMENDATIONS:
{cls._format_dict(cls.WEATHER_RULES)}
"""

    @staticmethod
    def _format_dict(d: dict, indent: int = 0) -> str:
        """Format a dictionary for display."""
        result = []
        for key, value in d.items():
            result.append(f"{'  ' * indent}- {key}: {value}")
        return "\n".join(result)
