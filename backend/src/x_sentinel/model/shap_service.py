class SHAPService:
    """Local SHAP adapter contract. Real implementation belongs to PLAN-08."""

    def explain(self, _model, _vector: list[float]) -> list[float]:
        raise NotImplementedError
