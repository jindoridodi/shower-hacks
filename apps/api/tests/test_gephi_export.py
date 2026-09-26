import io
import zipfile
import xml.etree.ElementTree as etree

from apps.api.services.discovery.models import CandidateSource
from apps.api.services.graph.gephi import csv_zip, gexf
from apps.api.services.graph.models import GraphExportRequest


def sample_request() -> GraphExportRequest:
    return GraphExportRequest(query="demo-user", candidates=[CandidateSource(url="https://github.com/demo-user", platform="GitHub", candidateUsername="demo-user", confidence="high", matchReason="match")], providerEvidence={"https://github.com/demo-user": ["sherlock", "maigret"]})


def test_csv_zip_has_gephi_tables() -> None:
    with zipfile.ZipFile(io.BytesIO(csv_zip(sample_request()))) as archive:
        assert set(archive.namelist()) == {"nodes.csv", "edges.csv"}
        assert archive.read("nodes.csv").decode().startswith("Id,Label,Type,Platform,URL,Confidence")


def test_gexf_is_valid_xml() -> None:
    root = etree.fromstring(gexf(sample_request()))
    assert root.tag.endswith("gexf")
