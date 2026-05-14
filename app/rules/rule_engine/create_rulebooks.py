import re
import json
import warnings
from typing import NamedTuple

import pandas as pd

from app.rules.vocabulary.mappings import get_id_maps

from app.rules.rulebooks.range_rules.crop_climate_rulebook          import ClimateRulebook
from app.rules.rulebooks.range_rules.soil_climate_rulebook          import SoilClimateRulebook
from app.rules.rulebooks.range_rules.water_climate_rulebook         import WaterClimateRulebook
from app.rules.rulebooks.range_rules.season_climate_rulebook        import SeasonClimateRulebook
from app.rules.rulebooks.threshold_rules.irrigation_frequency_rulebook  import IrrigationFrequencyRulebook
from app.rules.rulebooks.threshold_rules.irrigation_calender_rulebook      import IrrigationCalenderRulebook
from app.rules.rulebooks.threshold_rules.fertilization_calendar_rulebook   import FertilizationCalendarRulebook
from app.rules.rulebooks.threshold_rules.risk_thresholds_rulebook       import ThresholdRulebook
from app.rules.rulebooks.compatibility_rules.crop_soil_compatibility_rulebook              import CropSoilCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.crop_season_compatibility_rulebook            import CropSeasonCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.water_source_compatibility_rulebook           import WaterSourceCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.climate_compatibility_rulebook                import ClimateCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.soil_climate_compatibility_rulebook           import SoilClimateCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.irrigation_frequency_compatibility_rulebook   import IrrigationFrequencyCompatibilityRulebook
from app.rules.rulebooks.compatibility_rules.crop_type_season_compatibility_rulebook       import CropTypeSeasonCompatibilityRulebook
from app.rules.rulebooks.event_timeline.crop_type_timeline_rulebook                        import CropTypeTimelineRulebook
from app.rules.rulebooks.action_rules.soil_action_rulebook                  import SoilActionRulebook
from app.rules.rulebooks.action_rules.season_action_rulebook                import SeasonActionRulebook
from app.rules.rulebooks.action_rules.water_source_action_rulebook          import WaterSourceActionRulebook
from app.rules.rulebooks.action_rules.temperature_action_rulebook           import TemperatureActionRulebook
from app.rules.rulebooks.action_rules.humidity_action_rulebook              import HumidityActionRulebook
from app.rules.rulebooks.action_rules.soil_moisture_action_rulebook         import SoilMoistureActionRulebook
from app.rules.rulebooks.action_rules.ph_action_rulebook                    import PhActionRulebook
from app.rules.rulebooks.action_rules.sunlight_action_rulebook              import SunlightActionRulebook
from app.rules.rulebooks.action_rules.irrigation_frequency_action_rulebook  import IrrigationFrequencyActionRulebook
from app.rules.rulebooks.action_rules.rainfall_action_rulebook              import RainfallActionRulebook

warnings.filterwarnings('ignore')

# ── Feasibility vocabulary ────────────────────────────────────────────────────
FEASIBILITY_VALUES = ('Ideal', 'Conditional', 'Not Feasible')


def _check_feasibility(value: str, context: str = '') -> str:
    """Raise ValueError if *value* is not one of the three allowed feasibility
    labels, then return the value unchanged."""
    if value not in FEASIBILITY_VALUES:
        raise ValueError(
            f"Invalid feasibility '{value}'{' in ' + context if context else ''}. "
            f"Must be one of {FEASIBILITY_VALUES}."
        )
    return value


# ── Paths ─────────────────────────────────────────────────────────────────────
from pathlib import Path
_ROOT     = Path(__file__).parents[3]
CSV_PATH  = str(_ROOT / 'Data_Setup' / 'Datasets' / 'crop_recommendationV3.csv')
JSON_PATH = str(_ROOT / 'Data_Setup' / 'Datasets' / 'crop_rules.json')


# ── Return types ──────────────────────────────────────────────────────────────
class RangeRulebooks(NamedTuple):
    climate_df:        pd.DataFrame
    soil_chem_df:      pd.DataFrame
    water_df:          pd.DataFrame
    season_climate_df: pd.DataFrame


class CompatibilityRulebooks(NamedTuple):
    crop_soil_df:             pd.DataFrame
    crop_season_df:           pd.DataFrame
    water_source_df:          pd.DataFrame
    climate_df:               pd.DataFrame
    soil_climate_df:          pd.DataFrame
    irrigation_frequency_df:  pd.DataFrame
    crop_type_season_df:      pd.DataFrame


class ActionRulebooks(NamedTuple):
    soil_df:                 pd.DataFrame
    season_df:               pd.DataFrame
    water_source_df:         pd.DataFrame
    temperature_df:          pd.DataFrame
    humidity_df:             pd.DataFrame
    soil_moisture_df:        pd.DataFrame
    ph_df:                   pd.DataFrame
    sunlight_df:             pd.DataFrame
    irrigation_frequency_df: pd.DataFrame
    rainfall_df:             pd.DataFrame


# ── Loaders ───────────────────────────────────────────────────────────────────
def read_crop_data(file_path: str = CSV_PATH) -> pd.DataFrame | None:
    """Load crop CSV from disk."""
    try:
        df = pd.read_csv(file_path)
        df['label'] = df['label'].str.title()
        df['season'] = df['season'].str.title()
        return df
    except Exception as e:
        print(f"Error reading crop data: {e}")
        return None


def read_rules_json(file_path: str = JSON_PATH) -> dict:
    """Load crop rules JSON from disk."""
    with open(file_path, 'r') as f:
        return json.load(f)


# ── Private helpers ───────────────────────────────────────────────────────────
def _col_stats(grp: pd.DataFrame, col: str) -> dict:
    """Return min/max/mean/std for one column as {col_min, col_max, ...}."""
    s = grp[col]
    return {
        f"{col}_min":  round(float(s.min()),  4),
        f"{col}_max":  round(float(s.max()),  4),
        f"{col}_mean": round(float(s.mean()), 4),
    }


def _build_stats_df(
    df: pd.DataFrame,
    group_cols: list,
    value_cols: list,
    key_names: list,
    key_maps: dict | None = None,
) -> pd.DataFrame:
    """One row per group; each value_col expands to {col}_min/max/mean/std columns.
    key_maps: optional {key_name: {raw_val → id}} to convert string keys to integer IDs.
    """
    records = []
    for keys, grp in df.groupby(group_cols):
        keys = (keys,) if not isinstance(keys, tuple) else keys
        row = dict(zip(key_names, keys))
        for col in value_cols:
            row |= _col_stats(grp, col)
        records.append(row)
    result = pd.DataFrame(records)
    if key_maps:
        for col, mapping in key_maps.items():
            result[col] = result[col].map(mapping)
    return result


def _score_to_feasibility(score: float) -> str:
    """Derive a feasibility label from a numeric score.
    Used for sections that carry only scores (e.g. crop_type_season_suitability).
    Thresholds: score >= 0.7 → Ideal | >= 0.4 → Conditional | else → Not Feasible
    """
    if score >= 0.7:
        return FEASIBILITY_VALUES[0]   # 'Ideal'
    if score >= 0.4:
        return FEASIBILITY_VALUES[1]   # 'Conditional'
    return FEASIBILITY_VALUES[2]       # 'Not Feasible'


def _clean_key(key: str) -> str:
    """'>70' → 'above_70', '<40' → 'below_40', '15-20' → '15_20'."""
    key = re.sub(r'^>', 'above_', str(key))
    key = re.sub(r'^<', 'below_', key)
    return key.replace('-', '_').lower()


def _build_long(
    rules: dict,
    section_key: str,
    inner_key_col: str,
    crop_id_map: dict,
    inner_id_map: dict | None = None,
    filter_keys: list | None = None,
) -> pd.DataFrame:
    """Build a long-format compatibility DataFrame — one row per (crop, inner_key).

    Reads 'score' and 'feasibility' from each combined *_adjustment_rules entry.
    Maps the inner key to an integer ID when inner_id_map is provided.

    Output columns: crop_id, <inner_key_col>, score, feasibility
    """
    rows = []
    for crop, entries in rules[section_key].items():
        if crop.startswith('_'):
            continue
        for key in (filter_keys or entries.keys()):
            entry = entries[key]
            rows.append({
                'crop_id':     crop_id_map[crop],
                inner_key_col: inner_id_map[key] if inner_id_map else key,
                'score':       float(entry['score']),
                'feasibility': _check_feasibility(
                    entry['feasibility'],
                    context=f"{section_key}[{crop}][{key}]",
                ),
            })
    return pd.DataFrame(rows)


def _build_action_rows(
    rules: dict,
    section_key: str,
    band_col: str,
    crop_id_map: dict,
    inner_id_map: dict | None = None,
    filter_keys: list | None = None,
) -> pd.DataFrame:
    """Build an action/adjustment DataFrame — one row per (crop, band).

    Reads ONLY feasibility, reasoning, and actions from each entry.
    The 'score' key present in combined sections is intentionally excluded —
    adjustment rulebook models do not store a score column.

    Output columns: crop_id, <band_col>, feasibility, reasoning, actions (JSON string)
    """
    rows = []
    for crop, bands in rules[section_key].items():
        if crop.startswith('_'):
            continue
        for key in (filter_keys or bands.keys()):
            entry = bands[key]
            rows.append({
                'crop_id':     crop_id_map[crop],
                band_col:      inner_id_map[key] if inner_id_map else key,
                'feasibility': _check_feasibility(
                    entry['feasibility'],
                    context=f"{section_key}[{crop}][{key}]",
                ),
                'reasoning':   entry['reasoning'],
                'actions':     json.dumps(entry['actions']),
            })
    return pd.DataFrame(rows)


def _build_wide(rules: dict, section_key: str, prefix: str, crop_id_map: dict) -> pd.DataFrame:
    """Build a wide-format compatibility DataFrame — one row per crop.

    Creates a pair of columns per range key in the section:
      {prefix}{clean_key}             → score         (float)
      {prefix}{clean_key}_feasibility → feasibility   (str, one of FEASIBILITY_VALUES)

    Output columns: crop_id, {prefix}*, {prefix}*_feasibility  (interleaved per key)
    """
    rows = []
    for crop, entries in rules[section_key].items():
        if crop.startswith('_'):
            continue
        row = {'crop_id': crop_id_map[crop]}
        for k, entry in entries.items():
            col = f"{prefix}{_clean_key(k)}"
            row[col]                  = float(entry['score'])
            row[f"{col}_feasibility"] = _check_feasibility(
                entry['feasibility'],
                context=f"{section_key}[{crop}][{k}]",
            )
        rows.append(row)
    return pd.DataFrame(rows)


# ── Rulebook builders ─────────────────────────────────────────────────────────
def create_range_rules(crop_data: pd.DataFrame) -> RangeRulebooks:
    """Build climate, soil-chemistry, and water range rulebooks from CSV data.

    Keys    — climate_df / water_df : crop_id, growth_stage_id, soil_type_id
              soil_chem_df          : crop_id
    Columns — each feature expands to {feature}_min, {feature}_max, {feature}_mean, {feature}_std

    climate_df        features : temperature, humidity, sunlight_exposure, wind_speed,
                                 co2_concentration, crop_density, frost_risk
    soil_chem_df      features : N, P, K, ph, organic_matter, soil_moisture
    water_df          features : soil_moisture, rainfall
    season_climate_df key      : season_id
                      features : temperature, humidity, rainfall, sunlight_exposure,
                                 wind_speed, co2_concentration
    """
    CROP_ID         = get_id_maps()['Crop_Name']
    CROP_STAGE_SOIL = ['label', 'growth_stage', 'soil_type']
    OUT_STAGE_SOIL  = ['crop_id', 'growth_stage_id', 'soil_type_id']
    KEY_MAPS        = {'crop_id': CROP_ID}

    return RangeRulebooks(
        climate_df   = _build_stats_df(crop_data, CROP_STAGE_SOIL,
                           ['temperature', 'humidity', 'sunlight_exposure', 'wind_speed',
                            'co2_concentration', 'crop_density', 'frost_risk'],
                           OUT_STAGE_SOIL, KEY_MAPS),
        soil_chem_df = _build_stats_df(crop_data, ['label'],
                           ['N', 'P', 'K', 'ph', 'organic_matter', 'soil_moisture'],
                           ['crop_id'], KEY_MAPS),
        water_df     = _build_stats_df(crop_data, CROP_STAGE_SOIL,
                           ['soil_moisture', 'rainfall'],
                           OUT_STAGE_SOIL, KEY_MAPS),
        season_climate_df = _build_stats_df(crop_data, ['season'],
                           ['temperature', 'humidity', 'rainfall', 'sunlight_exposure',
                            'wind_speed', 'co2_concentration'],
                           ['season_id'], key_maps={'season_id': get_id_maps()['Season']}),
    )


def create_irrigation_rules(rules: dict) -> pd.DataFrame:
    """Build irrigation frequency rulebook from crop_rules.json.

    All 45 combinations (3 crops x 5 growth stages x 3 soil types) are
    explicitly defined in the JSON, so no CSV-derived gaps or missing stages.

    Keys    : crop_id, growth_stage_id, soil_type_id
    Columns : recommended_frequency, mean_frequency
    """
    _maps    = get_id_maps()
    CROP_ID  = _maps['Crop_Name']
    STAGE_ID = _maps['Growth_Stage']
    SOIL_ID  = _maps['Soil_Type']

    records = []
    for crop, stages in rules['irrigation_frequency_rules'].items():
        if crop.startswith('_'):
            continue
        for stage, soils in stages.items():
            for soil, freq in soils.items():
                records.append({
                    'crop_id':               CROP_ID[crop],
                    'growth_stage_id':       STAGE_ID[stage],
                    'soil_type_id':          SOIL_ID[soil],
                    'recommended_frequency': int(freq),
                    'mean_frequency':        float(freq),
                })
    return pd.DataFrame(records)


def create_threshold_rules(crop_data: pd.DataFrame) -> pd.DataFrame:
    """Build frost/wind/temperature threshold rulebook from CSV data.

    Keys    : crop_id, growth_stage_id
    Columns : frost_risk_caution, frost_risk_critical, wind_caution, wind_critical,
              temp_cold_caution, temp_cold_critical, temp_heat_caution, temp_heat_critical
    """
    CROP_ID = get_id_maps()['Crop_Name']
    records = []
    for (crop, stage), grp in crop_data.groupby(['label', 'growth_stage']):
        records.append({
            'crop_id':              CROP_ID[crop],
            'growth_stage_id':      int(stage),
            'frost_risk_caution':   round(float(grp['frost_risk'].quantile(0.75)), 2),
            'frost_risk_critical':  round(float(grp['frost_risk'].quantile(0.90)), 2),
            'wind_caution':         round(float(grp['wind_speed'].quantile(0.75)),  2),
            'wind_critical':        round(float(grp['wind_speed'].quantile(0.90)),  2),
            'temp_cold_caution':    round(float(grp['temperature'].quantile(0.25)), 2),
            'temp_cold_critical':   round(float(grp['temperature'].quantile(0.10)), 2),
            'temp_heat_caution':    round(float(grp['temperature'].quantile(0.75)), 2),
            'temp_heat_critical':   round(float(grp['temperature'].quantile(0.90)), 2),
        })
    return pd.DataFrame(records)


def create_irrigation_calender_rules(rules: dict) -> pd.DataFrame:
    """Build irrigation start rulebook from crop rules JSON.

    Keys    : crop_id
    Columns : days_after_sowing
    """
    CROP_ID = get_id_maps()['Crop_Name']
    records = []
    for crop, data in rules['CROP_RULES'].items():
        if crop.startswith('_'):
            continue
        records.append({
            'crop_id':           CROP_ID[crop.title()],
            'days_after_sowing': data['irrigation']['days_after_sowing'],
        })
    return pd.DataFrame(records)


def create_fertilization_calendar_rules(rules: dict) -> pd.DataFrame:
    """Build fertilization start rulebook from crop rules JSON.

    Keys    : crop_id
    Columns : days_after_sowing
    """
    CROP_ID = get_id_maps()['Crop_Name']
    records = []
    for crop, data in rules['CROP_RULES'].items():
        if crop.startswith('_'):
            continue
        records.append({
            'crop_id':           CROP_ID[crop.title()],
            'days_after_sowing': data['fertilizer']['days_after_sowing'],
        })
    return pd.DataFrame(records)


def create_compatibility_rules(rules: dict) -> CompatibilityRulebooks:
    """Build all compatibility DataFrames from the crop rules JSON dict.
    Scores and feasibility labels are read from the combined *_adjustment_rules sections.

    crop_soil_df         keys : crop_id, soil_type_id        columns : score, feasibility
    crop_season_df       keys : crop_id, season_id           columns : score, feasibility
    water_source_df      keys : crop_id, water_source_id     columns : score, feasibility
    climate_df           key  : crop_id   columns : temp_*, temp_*_feasibility,
                                                    humidity_*, humidity_*_feasibility,
                                                    sunlight_*, sunlight_*_feasibility
    soil_climate_df      key  : crop_id   columns : moisture_*, moisture_*_feasibility,
                                                    ph_*, ph_*_feasibility
    irrigation_frequency_df key : crop_id  columns : irr_freq_*, irr_freq_*_feasibility
    crop_type_season_df  keys : crop_type_id, season_id  columns : score, feasibility
    """
    _maps        = get_id_maps()
    CROP_ID      = _maps['Crop_Name']
    SOIL_ID      = _maps['Soil_Type']
    WATER_ID     = _maps['Water_Source']
    CROP_TYPE_ID = _maps['Crop_Type']
    SEASON_ID    = _maps['Season']

    crop_type_season_rows = [
        {
            'crop_type_id': CROP_TYPE_ID[ct],
            'season_id':    SEASON_ID[season.title()],
            'score':        score,
            'feasibility':  _score_to_feasibility(score),
        }
        for ct, seasons in rules['crop_type_season_suitability'].items()
        if not ct.startswith('_')
        for season, score in seasons.items()
    ]

    return CompatibilityRulebooks(
        crop_soil_df    = _build_long(rules, 'soil_adjustment_rules',         'soil_type_id',    CROP_ID, inner_id_map=SOIL_ID),
        crop_season_df  = _build_long(rules, 'season_adjustment_rules',       'season_id',       CROP_ID, inner_id_map=SEASON_ID),
        water_source_df = _build_long(rules, 'water_source_adjustment_rules', 'water_source_id', CROP_ID,
                              inner_id_map=WATER_ID, filter_keys=list(WATER_ID.keys())),
        climate_df      = (
                          _build_wide(rules, 'temperature_adjustment_rules', 'temp_',     CROP_ID)
                          .merge(_build_wide(rules, 'humidity_adjustment_rules',            'humidity_',  CROP_ID), on='crop_id')
                          .merge(_build_wide(rules, 'sunlight_adjustment_rules',            'sunlight_',  CROP_ID), on='crop_id')
                          ),
        soil_climate_df = (
                          _build_wide(rules, 'soil_moisture_adjustment_rules', 'moisture_', CROP_ID)
                          .merge(_build_wide(rules, 'ph_adjustment_rules',                  'ph_',        CROP_ID), on='crop_id')
                          ),
        irrigation_frequency_df = _build_wide(rules, 'irrigation_frequency_adjustment_rules', 'irr_freq_', CROP_ID),
        crop_type_season_df     = pd.DataFrame(crop_type_season_rows),
    )


def create_action_rules(rules: dict) -> ActionRulebooks:
    """Build all action/adjustment DataFrames from the crop rules JSON dict.

    soil_df                 keys : crop_id, soil_type_id (int)
    season_df               keys : crop_id, season_id (int)
    water_source_df         keys : crop_id, water_source_id (int)
    temperature_df          keys : crop_id, temp_range (str)
    humidity_df             keys : crop_id, humidity_range (str)
    soil_moisture_df        keys : crop_id, moisture_range (str)
    ph_df                   keys : crop_id, ph_category (str)
    sunlight_df             keys : crop_id, sunlight_range (str)
    irrigation_frequency_df keys : crop_id, irr_freq_range (str)
    rainfall_df             keys : crop_id, rainfall_range (str)

    All tables include : feasibility, reasoning, actions (JSON-serialised array of action objects)
    """
    _maps    = get_id_maps()
    CROP_ID  = _maps['Crop_Name']
    SOIL_ID  = _maps['Soil_Type']
    SEASON_ID = _maps['Season']
    WATER_ID = _maps['Water_Source']

    return ActionRulebooks(
        soil_df                 = _build_action_rows(rules, 'soil_adjustment_rules',
                                      'soil_type_id', CROP_ID, inner_id_map=SOIL_ID),
        season_df               = _build_action_rows(rules, 'season_adjustment_rules',
                                      'season_id', CROP_ID, inner_id_map=SEASON_ID),
        water_source_df         = _build_action_rows(rules, 'water_source_adjustment_rules',
                                      'water_source_id', CROP_ID,
                                      inner_id_map=WATER_ID, filter_keys=list(WATER_ID.keys())),
        temperature_df          = _build_action_rows(rules, 'temperature_adjustment_rules',
                                      'temp_range', CROP_ID),
        humidity_df             = _build_action_rows(rules, 'humidity_adjustment_rules',
                                      'humidity_range', CROP_ID),
        soil_moisture_df        = _build_action_rows(rules, 'soil_moisture_adjustment_rules',
                                      'moisture_range', CROP_ID),
        ph_df                   = _build_action_rows(rules, 'ph_adjustment_rules',
                                      'ph_category', CROP_ID),
        sunlight_df             = _build_action_rows(rules, 'sunlight_adjustment_rules',
                                      'sunlight_range', CROP_ID),
        irrigation_frequency_df = _build_action_rows(rules, 'irrigation_frequency_adjustment_rules',
                                      'irr_freq_range', CROP_ID),
        rainfall_df             = _build_action_rows(rules, 'rainfall_adjustment_rules',
                                      'rainfall_range', CROP_ID),
    )



def create_crop_type_timeline(rules: dict) -> pd.DataFrame:
    """Build crop-type sowing/harvest calendar from the crop rules JSON.

    Keys    : crop_type_id (int)
    Columns : sow_start_month, sow_end_month, harvest_start_month, harvest_end_month
    """
    CROP_TYPE_ID = get_id_maps()['Crop_Type']
    rows = []
    for crop_type, cal in rules['crop_type_calendar'].items():
        rows.append({
            'crop_type_id':       CROP_TYPE_ID[crop_type],
            'sow_start_month':     cal['sow_start'],
            'sow_end_month':       cal['sow_end'],
            'harvest_start_month': cal['harvest_start'],
            'harvest_end_month':   cal['harvest_end'],
        })
    return pd.DataFrame(rows)


# ── Seeder ────────────────────────────────────────────────────────────────────
class RulebookSeeder:

    def __init__(self, db):
        self.db = db

    def seed_all(self, crop_data: pd.DataFrame, rules: dict) -> None:
        range_books      = create_range_rules(crop_data)
        irr_df           = create_irrigation_rules(rules)
        threshold_df     = create_threshold_rules(crop_data)
        irr_start_df          = create_irrigation_calender_rules(rules)
        fert_calendar_df      = create_fertilization_calendar_rules(rules)
        crop_type_timeline_df = create_crop_type_timeline(rules)
        compat_books          = create_compatibility_rules(rules)
        action_books          = create_action_rules(rules)

        self._clear_tables()

        # Range rules
        self._seed_df(ClimateRulebook,       range_books.climate_df)
        self._seed_df(SoilClimateRulebook,   range_books.soil_chem_df)
        self._seed_df(WaterClimateRulebook,  range_books.water_df)
        self._seed_df(SeasonClimateRulebook, range_books.season_climate_df)

        # Threshold rules
        self._seed_df(IrrigationFrequencyRulebook, irr_df)
        self._seed_df(IrrigationCalenderRulebook, irr_start_df)
        self._seed_df(FertilizationCalendarRulebook, fert_calendar_df)
        self._seed_df(ThresholdRulebook, threshold_df)

        # Crop-type timeline
        self._seed_df(CropTypeTimelineRulebook, crop_type_timeline_df)

        # Compatibility rules
        self._seed_df(CropSoilCompatibilityRulebook,            compat_books.crop_soil_df)
        self._seed_df(CropSeasonCompatibilityRulebook,          compat_books.crop_season_df)
        self._seed_df(WaterSourceCompatibilityRulebook,         compat_books.water_source_df)
        self._seed_df(ClimateCompatibilityRulebook,             compat_books.climate_df)
        self._seed_df(SoilClimateCompatibilityRulebook,         compat_books.soil_climate_df)
        self._seed_df(IrrigationFrequencyCompatibilityRulebook, compat_books.irrigation_frequency_df)
        self._seed_df(CropTypeSeasonCompatibilityRulebook,      compat_books.crop_type_season_df)

        # Action rules
        self._seed_df(SoilActionRulebook,                  action_books.soil_df)
        self._seed_df(SeasonActionRulebook,                action_books.season_df)
        self._seed_df(WaterSourceActionRulebook,           action_books.water_source_df)
        self._seed_df(TemperatureActionRulebook,           action_books.temperature_df)
        self._seed_df(HumidityActionRulebook,              action_books.humidity_df)
        self._seed_df(SoilMoistureActionRulebook,          action_books.soil_moisture_df)
        self._seed_df(PhActionRulebook,                    action_books.ph_df)
        self._seed_df(SunlightActionRulebook,              action_books.sunlight_df)
        self._seed_df(IrrigationFrequencyActionRulebook,   action_books.irrigation_frequency_df)
        self._seed_df(RainfallActionRulebook,              action_books.rainfall_df)

        self.db.session.commit()

    def _seed_df(self, model, df: pd.DataFrame) -> None:
        self.db.session.bulk_save_objects(
            [model(**row) for row in df.to_dict(orient='records')]
        )

    def _clear_tables(self):
        for model in [
            # Action rules first (no FK deps)
            SoilActionRulebook, SeasonActionRulebook, WaterSourceActionRulebook,
            TemperatureActionRulebook, HumidityActionRulebook, SoilMoistureActionRulebook,
            PhActionRulebook, SunlightActionRulebook, IrrigationFrequencyActionRulebook,
            RainfallActionRulebook,
            # Crop-type timeline
            CropTypeTimelineRulebook,
            # Compatibility rules
            CropSoilCompatibilityRulebook, CropSeasonCompatibilityRulebook,
            WaterSourceCompatibilityRulebook, ClimateCompatibilityRulebook,
            SoilClimateCompatibilityRulebook, IrrigationFrequencyCompatibilityRulebook,
            CropTypeSeasonCompatibilityRulebook,
            # Range / threshold rules
            ClimateRulebook, SoilClimateRulebook, WaterClimateRulebook, SeasonClimateRulebook,
            IrrigationFrequencyRulebook, IrrigationCalenderRulebook, FertilizationCalendarRulebook, ThresholdRulebook,
        ]:
            model.query.delete()


def run(db):
    seeder    = RulebookSeeder(db)
    crop_data = read_crop_data()
    rules     = read_rules_json()
    seeder.seed_all(crop_data, rules)

