from pathlib import Path

from sales_ivr.catalog.loader import filter_by_state, load_catalog
from sales_ivr.compliance.loader import list_available_states, load_state_compliance
from sales_ivr.config import InsuranceProduct, resolve_path
from sales_ivr.pricing.engine import PricingEngine, load_objection_corpus


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_catalog_has_eight_products():
    catalog_dir = _project_root() / "sales_ivr" / "catalog" / "products"
    products = load_catalog(catalog_dir)
    assert len(products) >= 8
    assert all(isinstance(p, InsuranceProduct) for p in products)


def test_filter_catalog_by_state():
    catalog_dir = _project_root() / "sales_ivr" / "catalog" / "products"
    products = load_catalog(catalog_dir)
    ca_products = filter_by_state(products, "CA")
    assert any(p.product_id == "auto-personal" for p in ca_products)


def test_compliance_packs():
    compliance_dir = _project_root() / "sales_ivr" / "compliance" / "disclosures"
    states = list_available_states(compliance_dir)
    assert "CA" in states
    pack = load_state_compliance(compliance_dir, "CA")
    assert len(pack.disclosures) >= 2


def test_pricing_engine():
    catalog_dir = _project_root() / "sales_ivr" / "catalog" / "products"
    products = load_catalog(catalog_dir)
    engine = PricingEngine()
    monthly, annual, summary = engine.calculate_for_product_id(
        products,
        "auto-personal",
        "auto-standard",
        {"driver_age": 1.1, "vehicle_year": 1.0, "annual_mileage": 0.95},
    )
    assert monthly > 0
    assert annual > monthly
    assert "Personal Auto" in summary


def test_objection_corpus():
    objections_dir = _project_root() / "sales_ivr" / "knowledge" / "objections"
    corpus = load_objection_corpus(objections_dir)
    assert "price" in corpus
    assert "competitor" in corpus
