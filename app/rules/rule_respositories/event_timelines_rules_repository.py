from app.rules.rulebooks.event_timeline.crop_type_timeline_rulebook import CropTypeTimelineRulebook


class EventTimelinesRulesRepository:

    # Crop Type Timeline (key: crop_type_id)
    @staticmethod
    def get_all_crop_type_timelines() -> list:
        return CropTypeTimelineRulebook.query.all()

    @staticmethod
    def get_timeline_by_crop_type(crop_type_id: int) -> CropTypeTimelineRulebook:
        return CropTypeTimelineRulebook.query.filter_by(crop_type_id=crop_type_id).first()
