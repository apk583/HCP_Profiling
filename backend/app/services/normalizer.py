"""Normalize raw collector data into unified HCP profile structures."""

import logging
from datetime import datetime
from typing import Any

from app.schemas.hcp import (
    Address,
    AdverseEventSummary,
    ClinicalTrial,
    HCPProfile,
    MLFeatures,
    NPIData,
    Publication,
    SourceResult,
)

logger = logging.getLogger(__name__)


class ProfileNormalizer:
    def normalize(
        self,
        npi: str,
        raw_data: dict[str, Any],
        source_results: list[SourceResult],
    ) -> HCPProfile:
        identity = self._normalize_npi(raw_data.get("npi_registry", {}), npi)
        publications = self._normalize_publications(raw_data.get("pubmed", {}))
        trials = self._normalize_trials(raw_data.get("clinical_trials", {}))
        adverse = self._normalize_adverse(raw_data.get("openfda", {}))

        features = self._compute_features(identity, publications, trials, adverse)

        return HCPProfile(
            npi=npi,
            identity=identity,
            publications=publications,
            clinical_trials=trials,
            adverse_events=adverse,
            features=features,
            source_results=source_results,
            generated_at=datetime.utcnow(),
        )

    def _normalize_npi(self, raw: dict[str, Any], npi: str) -> NPIData:
        results = raw.get("results", [])
        if not results:
            return NPIData(npi=npi)

        record = results[0]
        basic = record.get("basic", {})
        taxonomies = record.get("taxonomies", [])
        addresses = record.get("addresses", [])

        primary_tax = next((t for t in taxonomies if t.get("primary")), taxonomies[0] if taxonomies else {})
        practice_addr = next(
            (a for a in addresses if a.get("address_purpose") == "LOCATION"),
            addresses[0] if addresses else {},
        )

        entity_type_code = record.get("enumeration_type", "")
        entity_type = "Individual" if entity_type_code == "NPI-1" else "Organization"

        return NPIData(
            npi=npi,
            entity_type=entity_type,
            first_name=basic.get("first_name", ""),
            last_name=basic.get("last_name", ""),
            organization_name=basic.get("organization_name", ""),
            credential=basic.get("credential", ""),
            taxonomy_code=primary_tax.get("code", ""),
            taxonomy_description=primary_tax.get("desc", ""),
            primary_specialty=primary_tax.get("desc", ""),
            address=Address(
                line1=practice_addr.get("address_1", ""),
                line2=practice_addr.get("address_2", ""),
                city=practice_addr.get("city", ""),
                state=practice_addr.get("state", ""),
                postal_code=practice_addr.get("postal_code", ""),
                country=practice_addr.get("country_code", "US"),
            ),
            phone=practice_addr.get("telephone_number", ""),
            enumeration_date=basic.get("enumeration_date", ""),
            last_updated=basic.get("last_updated", ""),
            status=basic.get("status", ""),
        )

    def _normalize_publications(self, raw: dict[str, Any]) -> list[Publication]:
        return [Publication(**p) for p in raw.get("publications", [])]

    def _normalize_trials(self, raw: dict[str, Any]) -> list[ClinicalTrial]:
        return [ClinicalTrial(**t) for t in raw.get("trials", [])]

    def _normalize_adverse(self, raw: dict[str, Any]) -> list[AdverseEventSummary]:
        return [AdverseEventSummary(**a) for a in raw.get("adverse_events", [])]

    def _compute_features(
        self,
        identity: NPIData,
        publications: list[Publication],
        trials: list[ClinicalTrial],
        adverse: list[AdverseEventSummary],
    ) -> MLFeatures:
        last_name = identity.last_name.lower()
        first_author_count = sum(
            1 for p in publications if p.authors and p.authors[0].lower().startswith(last_name)
        )
        pi_count = sum(1 for t in trials if "principal" in t.role.lower())

        collaborator_counts: dict[str, int] = {}
        for publication in publications:
            for author in publication.authors:
                parts = author.lower().replace(".", "").split() if author else []
                is_primary = bool(parts and identity.last_name and parts[0] == identity.last_name.lower() and (len(parts) == 1 or not identity.first_name or parts[1].startswith(identity.first_name[:1].lower())))
                if author and not is_primary:
                    collaborator_counts[author] = collaborator_counts.get(author, 0) + 1
        collaboration_total = sum(collaborator_counts.values())
        collaborator_count = len(collaborator_counts)

        years_active = 0
        if identity.enumeration_date:
            try:
                enum_date = datetime.strptime(identity.enumeration_date, "%Y-%m-%d")
                years_active = max(0, (datetime.utcnow() - enum_date).days // 365)
            except ValueError:
                years_active = 0

        return MLFeatures(
            publication_count=len(publications),
            first_author_count=first_author_count,
            clinical_trial_count=len(trials),
            pi_trial_count=pi_count,
            collaborator_count=collaborator_count,
            unique_collaborator_count=collaborator_count,
            strongest_collaboration_count=max(collaborator_counts.values(), default=0),
            average_collaboration_strength=round(collaboration_total / collaborator_count, 2) if collaborator_count else 0.0,
            collaboration_network_density=round(collaboration_total / (len(publications) * collaborator_count), 3) if publications and collaborator_count else 0.0,
            recurring_collaborator_ratio=round(sum(1 for count in collaborator_counts.values() if count > 1) / collaborator_count, 3) if collaborator_count else 0.0,
            years_active=years_active,
            adverse_event_reports=sum(a.event_count for a in adverse),
        )

    @staticmethod
    def provider_display_name(identity: NPIData) -> str:
        if identity.organization_name:
            return identity.organization_name
        parts = [identity.first_name, identity.last_name]
        if identity.credential:
            parts.append(identity.credential)
        return " ".join(p for p in parts if p).strip()

    @staticmethod
    def author_search_name(identity: NPIData) -> str:
        if identity.last_name and identity.first_name:
            return f"{identity.last_name} {identity.first_name[0]}"
        return identity.last_name or identity.organization_name
