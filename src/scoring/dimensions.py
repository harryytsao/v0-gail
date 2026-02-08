from dataclasses import dataclass


@dataclass
class DimensionConfig:
    name: str
    description: str
    signal_types: list[str]
    signal_weights: dict[str, float]
    default_score: float = 50.0
    min_score: float = 0.0
    max_score: float = 100.0


DIMENSIONS: dict[str, DimensionConfig] = {
    "responsiveness": DimensionConfig(
        name="responsiveness",
        description="How actively and deeply the user engages in conversations",
        signal_types=["communication_style", "cooperation"],
        signal_weights={
            "communication_style.verbosity": 0.3,
            "cooperation.provides_context": 0.4,
            "cooperation.follows_instructions": 0.3,
        },
    ),
    "escalation_risk": DimensionConfig(
        name="escalation_risk",
        description="Likelihood of the user becoming frustrated or confrontational",
        signal_types=["temperament", "sentiment"],
        signal_weights={
            "temperament.score_inverted": 0.4,  # low temperament → high risk
            "sentiment.frustration_detected": 0.3,
            "sentiment.overall_inverted": 0.3,
        },
    ),
    "engagement_quality": DimensionConfig(
        name="engagement_quality",
        description="Depth and richness of user engagement",
        signal_types=["communication_style", "topics", "cooperation"],
        signal_weights={
            "communication_style.technicality": 0.3,
            "communication_style.structured": 0.2,
            "topics.diversity": 0.2,
            "cooperation.provides_context": 0.3,
        },
    ),
    "cooperation_level": DimensionConfig(
        name="cooperation_level",
        description="How cooperative and pleasant the user is to interact with",
        signal_types=["cooperation", "temperament", "sentiment"],
        signal_weights={
            "cooperation.follows_instructions": 0.3,
            "cooperation.politeness": 0.3,
            "temperament.score": 0.2,
            "sentiment.overall": 0.2,
        },
    ),
    "expertise_level": DimensionConfig(
        name="expertise_level",
        description="User's technical knowledge and domain expertise",
        signal_types=["communication_style", "life_stage"],
        signal_weights={
            "communication_style.technicality": 0.5,
            "communication_style.formality": 0.1,
            "life_stage.domain_count": 0.2,
            "life_stage.confidence": 0.2,
        },
    ),
}
