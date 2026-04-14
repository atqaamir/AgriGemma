from app.models.pesticide import Pesticide
from app.models.pesticide_use import PesticideUse
from app.extensions import db


def get_all_pesticides():
    pesticides = Pesticide.query.filter_by(is_active=True).all()
    return [p.to_dict() for p in pesticides]


def get_pesticides_by_crop(crop_type: str):
    pesticides = Pesticide.query.filter_by(
        crop_type=crop_type,
        is_active=True
    ).all()
    return [p.to_dict() for p in pesticides]


def get_pesticides_by_target_pest(target_pest: str):
    pesticides = Pesticide.query.filter_by(
        target_pest=target_pest,
        is_active=True
    ).all()
    return [p.to_dict() for p in pesticides]


def recommend_pesticides(crop_type: str = None, target_pest: str = None):
    query = Pesticide.query.filter_by(is_active=True)

    if crop_type:
        query = query.filter_by(crop_type=crop_type)

    if target_pest:
        query = query.filter_by(target_pest=target_pest)

    pesticides = query.all()
    return [p.to_dict() for p in pesticides]


def log_pesticide_use(field_id: int, pesticide_id: int, dosage_used: str = None, notes: str = None):
    use = PesticideUse(
        field_id=field_id,
        pesticide_id=pesticide_id,
        dosage_used=dosage_used,
        notes=notes
    )

    db.session.add(use)
    db.session.commit()

    return use.to_dict()