from marshmallow import Schema, fields


class RiskItemSchema(Schema):
    risk = fields.Str()
    severity = fields.Str()
    mitigation = fields.Str()


class InsightItemSchema(Schema):
    insight = fields.Str()
    category = fields.Str()


class TaskIntelligenceSchema(Schema):
    """Typed output contract for the AI task intelligence overview."""
    summary = fields.Str()
    priority_level = fields.Str()
    recommendations = fields.List(fields.Str())
    urgent_actions = fields.List(fields.Str())
    risks = fields.List(fields.Nested(RiskItemSchema))
    insights = fields.List(fields.Nested(InsightItemSchema))
    generated_at = fields.Str()
    is_fallback = fields.Bool()
