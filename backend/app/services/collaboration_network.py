"""Build and cache publication collaboration networks."""

from collections import Counter, defaultdict
from app.schemas.hcp import CollaborationEdge, CollaborationMetrics, CollaborationNetwork, CollaborationNode, HCPProfile, Publication
from app.services.normalizer import ProfileNormalizer


def _author_key(name: str) -> str:
    return " ".join(name.lower().replace(".", "").split())


def _is_primary_author(author: str, profile: HCPProfile) -> bool:
    """Match PubMed's `Last ForeName` / `Last F` forms to the searched HCP."""
    parts = _author_key(author).split()
    last = _author_key(profile.identity.last_name)
    first = _author_key(profile.identity.first_name)
    return bool(parts and last and parts[0] == last and (len(parts) == 1 or not first or parts[1].startswith(first[:1])))


class CollaborationNetworkBuilder:
    """Creates a star network around the searched HCP from PubMed authors."""

    def build(self, profile: HCPProfile) -> CollaborationNetwork:
        hcp_name = ProfileNormalizer.provider_display_name(profile.identity) or profile.npi
        collaborators: Counter[str] = Counter()
        papers: dict[str, list[Publication]] = defaultdict(list)

        for publication in profile.publications:
            for author in publication.authors:
                if author and not _is_primary_author(author, profile):
                    collaborators[author] += 1
                    papers[author].append(publication)

        ranked = collaborators.most_common()
        strongest_name, strongest_count = ranked[0] if ranked else ("", 0)
        total = sum(collaborators.values())
        unique = len(collaborators)
        density = round(total / (len(profile.publications) * unique), 3) if profile.publications and unique else 0.0
        metrics = CollaborationMetrics(
            total_publications=len(profile.publications), total_collaborators=total,
            unique_collaborators=unique, strongest_collaborator=strongest_name,
            max_shared_publications=strongest_count,
            average_collaborations_per_author=round(total / unique, 2) if unique else 0.0,
            collaboration_network_density=density,
        )
        nodes = [CollaborationNode(id="hcp", label=hcp_name, type="hcp", npi=profile.npi, publication_count=len(profile.publications))]
        edges: list[CollaborationEdge] = []
        for index, (author, count) in enumerate(ranked):
            author_id = f"author-{index}"
            nodes.append(CollaborationNode(id=author_id, label=author, type="author", publication_count=len(papers[author]), shared_publications=count, publications=papers[author]))
            edges.append(CollaborationEdge(source="hcp", target=author_id, weight=count))
        return CollaborationNetwork(hcp={"name": hcp_name, "npi": profile.npi}, metrics=metrics, nodes=nodes, edges=edges)
