"""PubMed E-utilities collector."""

import logging
import xml.etree.ElementTree as ET
from typing import Any

from app.services.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class PubMedCollector(BaseCollector):
    source_name = "pubmed"

    async def collect(self, npi: str, **kwargs: Any) -> dict[str, Any]:
        author_name: str = kwargs.get("author_name", "")
        if not author_name:
            return {"publications": [], "pmids": []}

        base = self.settings.pubmed_base_url
        search_params = {
            "db": "pubmed",
            "term": f'"{author_name}"[Author]',
            "retmax": "25",
            "retmode": "json",
        }
        search_data = await self._get_with_retry(f"{base}esearch.fcgi", params=search_params)
        if not isinstance(search_data, dict):
            return {"publications": [], "pmids": []}

        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            logger.info("PubMed: no publications for %s", author_name)
            return {"publications": [], "pmids": []}

        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids[:25]),
            "retmode": "xml",
        }
        xml_text = await self._get_with_retry(f"{base}efetch.fcgi", params=fetch_params)
        publications = self._parse_pubmed_xml(xml_text if isinstance(xml_text, str) else "")
        logger.info("PubMed: found %d publications for %s", len(publications), author_name)
        return {"publications": publications, "pmids": pmids}

    def _parse_pubmed_xml(self, xml_text: str) -> list[dict[str, Any]]:
        if not xml_text.strip():
            return []
        publications: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            title_el = article.find(".//ArticleTitle")
            journal_el = article.find(".//Journal/Title")
            pub_date = self._extract_date(article)
            authors = [
                self._author_name(a)
                for a in article.findall(".//Author")
                if self._author_name(a)
            ]
            publications.append(
                {
                    "pmid": pmid_el.text if pmid_el is not None else "",
                    "title": title_el.text if title_el is not None else "",
                    "journal": journal_el.text if journal_el is not None else "",
                    "pub_date": pub_date,
                    "authors": authors,
                }
            )
        return publications

    @staticmethod
    def _author_name(author_el: ET.Element) -> str:
        last = author_el.find("LastName")
        fore = author_el.find("ForeName")
        if last is not None and fore is not None:
            return f"{last.text} {fore.text}"
        collective = author_el.find("CollectiveName")
        return collective.text if collective is not None else ""

    @staticmethod
    def _extract_date(article: ET.Element) -> str:
        pub_date = article.find(".//PubDate")
        if pub_date is None:
            return ""
        year = pub_date.find("Year")
        month = pub_date.find("Month")
        parts = [p.text for p in (year, month) if p is not None and p.text]
        return "-".join(parts)
