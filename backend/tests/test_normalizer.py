"""Tests for profile normalizer."""

from app.schemas.hcp import SourceResult
from app.services.normalizer import ProfileNormalizer


def test_normalize_npi_data():
    normalizer = ProfileNormalizer()
    raw = {
        "npi_registry": {
            "result_count": 1,
            "results": [
                {
                    "enumeration_type": "NPI-1",
                    "basic": {
                        "first_name": "JOHN",
                        "last_name": "SMITH",
                        "credential": "MD",
                        "enumeration_date": "2010-05-15",
                        "status": "A",
                    },
                    "taxonomies": [
                        {"code": "207R00000X", "desc": "Internal Medicine", "primary": True}
                    ],
                    "addresses": [
                        {
                            "address_purpose": "LOCATION",
                            "address_1": "123 Main St",
                            "city": "Boston",
                            "state": "MA",
                            "postal_code": "02101",
                            "telephone_number": "617-555-0100",
                        }
                    ],
                }
            ],
        },
        "pubmed": {"publications": [{"pmid": "123", "title": "Test Paper", "authors": ["Smith J"]}]},
        "clinical_trials": {"trials": []},
        "openfda": {"adverse_events": []},
    }
    profile = normalizer.normalize("1234567890", raw, [SourceResult(source="npi_registry", success=True)])
    assert profile.npi == "1234567890"
    assert profile.identity.first_name == "JOHN"
    assert profile.identity.last_name == "SMITH"
    assert profile.features.publication_count == 1


def test_author_search_name():
    from app.schemas.hcp import NPIData

    identity = NPIData(npi="1234567890", first_name="John", last_name="Smith")
    assert ProfileNormalizer.author_search_name(identity) == "Smith J"
