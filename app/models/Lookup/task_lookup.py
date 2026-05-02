"""
Task category → task type lookup table.
Single source of truth used by the API endpoint and anywhere
task types need to be validated or listed.
"""

TASK_CATEGORIES = ["crop", "field", "general"]

TASK_TYPE_BY_CATEGORY = {
    "crop": [
        {"value": "irrigation",   "label": "Irrigation"},
        {"value": "spraying",     "label": "Spraying"},
        {"value": "harvesting",   "label": "Harvesting"},
        {"value": "pruning",      "label": "Pruning"},
        {"value": "pollination",  "label": "Pollination"},
        {"value": "defoliation",  "label": "Defoliation"},
    ],
    "field": [
        {"value": "fertilizing",      "label": "Fertilizing"},
        {"value": "soil_testing",     "label": "Soil Testing"},
        {"value": "drainage",         "label": "Drainage"},
        {"value": "plowing",          "label": "Plowing"},
        {"value": "weeding",          "label": "Weeding"},
        {"value": "land_preparation", "label": "Land Preparation"},
    ],
    "general": [
        {"value": "maintenance",     "label": "Maintenance"},
        {"value": "inspection",      "label": "Inspection"},
        {"value": "equipment_check", "label": "Equipment Check"},
    ],
}

# Flat set of all valid task types — useful for validation
ALL_TASK_TYPES = {
    t["value"]
    for types in TASK_TYPE_BY_CATEGORY.values()
    for t in types
}
