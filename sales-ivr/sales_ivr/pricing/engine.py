from __future__ import annotations

from pathlib import Path

from sales_ivr.catalog.loader import get_product
from sales_ivr.config import InsuranceProduct


class PricingEngine:
    """Deterministic premium calculator — used by QuoteGenerationAgent later."""

    DEFAULT_FACTORS: dict[str, float] = {
        "driver_age": 1.0,
        "vehicle_year": 1.0,
        "annual_mileage": 1.0,
        "home_value": 1.0,
        "coverage_tier": 1.0,
    }

    def calculate(
        self,
        product: InsuranceProduct,
        tier_id: str,
        factors: dict[str, float],
    ) -> tuple[float, float, str]:
        tier = next((t for t in product.tiers if t.tier_id == tier_id), product.tiers[0])
        multiplier = 1.0
        for key, value in factors.items():
            if key in self.DEFAULT_FACTORS:
                multiplier *= value

        monthly = round(tier.base_premium_monthly * multiplier, 2)
        annual = round(monthly * 12 * 0.95, 2)  # annual pay discount
        summary = (
            f"{product.name} ({tier.name}): ${monthly:.2f}/mo or ${annual:.2f}/yr, "
            f"limit {tier.coverage_limit}"
        )
        return monthly, annual, summary

    def calculate_for_product_id(
        self,
        products: list[InsuranceProduct],
        product_id: str,
        tier_id: str,
        factors: dict[str, float],
    ) -> tuple[float, float, str]:
        product = get_product(products, product_id)
        if product is None:
            raise ValueError(f"Unknown product_id: {product_id}")
        return self.calculate(product, tier_id, factors)


def load_objection_corpus(objections_dir: Path) -> dict[str, str]:
    corpus: dict[str, str] = {}
    for path in sorted(objections_dir.glob("*.md")):
        corpus[path.stem] = path.read_text(encoding="utf-8")
    return corpus
