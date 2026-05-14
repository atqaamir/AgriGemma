def get_vocabulary():
    """ID → name mappings for all vocabulary tables. All values are {int: str}."""
    return {
        "Crop_Name": {
            1: "Maize",
            2: "Rice",
            3: "Cotton"
        },
        "Growth_Stage": {
            1: "Seedling",
            2: "Vegetative",
            3: "Flowering"
        },
        "Soil_Type": {
            1: "Sandy",
            2: "Loamy",
            3: "Clay"
        },
        "Water_Source": {
            1: "River",
            2: "Groundwater",
            3: "Recycled"
        },
        # Four real agricultural seasons for Pakistan.
        "Season": {
            1: "Rainy",
            2: "Winter",
            3: "Summer",
            4: "Fall"
        },
        # Crop type vocabulary (Kharif/Rabi/Zaid classification).
        "Crop_Type": {
            1: "Kharif",
            2: "Rabi",
            3: "Zaid"
        },
    }


def get_id_maps():
    """Return name→id lookup dicts, inverted from get_vocabulary()."""
    return {
        category: {name: id_ for id_, name in mapping.items()}
        for category, mapping in get_vocabulary().items()
    }

# Crop → crop-type label.  Kept here (not in DB) to avoid a redundant FK column.
# All current crops are Kharif; update when Rabi/Zaid crops are added.
CROP_TYPE_MAP = {
    "Maize":  1,
    "Rice":   1,
    "Cotton": 1,
}

# Pakistan 4-season month ranges (for UI / avoid-sowing logic).
# Keys are Season vocab IDs (1=Rainy, 2=Winter, 3=Summer, 4=Fall).
# end < start means the season wraps the calendar year.
#   1 rainy  (Kharif/Monsoon)  : Jul – Sep  (07–09)
#   2 winter (Rabi)            : Nov – Mar  (11–03, wraps year)
#   3 summer (pre-monsoon hot) : Apr – Jun  (04–06)
#   4 fall   (post-monsoon)    : Oct – Nov  (10–11)
SEASON_MONTHS = {
    1: {"start": 7,  "end": 9},
    2: {"start": 11, "end": 3},
    3: {"start": 4,  "end": 6},
    4: {"start": 10, "end": 11},
}
