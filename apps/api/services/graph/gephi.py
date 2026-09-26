"""In-memory CSV ZIP and GEXF exports for offline Gephi analysis."""

from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass

import xml.etree.ElementTree as etree

from apps.api.services.discovery.normalize import normalize_url
from apps.api.services.graph.models import GraphExportRequest


def _node_id(node_type: str, value: str) -> str:
    return hashlib.sha256(f"{node_type}:{value}".encode()).hexdigest()


def _safe(value: object) -> str:
    text = str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


@dataclass(frozen=True)
class GraphData:
    nodes: list[dict[str, str]]
    edges: list[dict[str, str]]


def build_graph(request: GraphExportRequest) -> GraphData:
    nodes: dict[str, dict[str, str]] = {}
    edges: dict[tuple[str, str, str], dict[str, str]] = {}

    def node(node_type: str, value: str, **attributes: str) -> str:
        identifier = _node_id(node_type, value)
        nodes.setdefault(identifier, {"Id": identifier, "Label": value, "Type": node_type, **attributes})
        return identifier

    username_id = node("username", request.query, Platform="", URL="", Confidence="")
    for candidate in request.candidates:
        url = normalize_url(candidate.url)
        url_id = node("public_url", url, Platform=candidate.platform, URL=url, Confidence=candidate.confidence)
        edges[(username_id, url_id, "possible_profile")] = {
            "Source": username_id, "Target": url_id, "Type": "Directed", "Label": "possible_profile",
            "Weight": str({"high": 3, "medium": 2, "low": 1}[candidate.confidence]),
        }
        for provider in sorted(set(request.provider_evidence.get(url, []))):
            provider_id = node("provider", provider, Platform="", URL="", Confidence="")
            edges[(username_id, provider_id, "discovered_by")] = {
                "Source": username_id, "Target": provider_id, "Type": "Directed", "Label": "discovered_by", "Weight": "1",
            }
            edges[(provider_id, url_id, "reported")] = {
                "Source": provider_id, "Target": url_id, "Type": "Directed", "Label": "reported", "Weight": "1",
            }
    return GraphData(nodes=sorted(nodes.values(), key=lambda item: item["Id"]), edges=sorted(edges.values(), key=lambda item: (item["Source"], item["Target"], item["Label"])))


def csv_zip(request: GraphExportRequest) -> bytes:
    graph = build_graph(request)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, rows, headers in (
            ("nodes.csv", graph.nodes, ["Id", "Label", "Type", "Platform", "URL", "Confidence"]),
            ("edges.csv", graph.edges, ["Source", "Target", "Type", "Label", "Weight"]),
        ):
            content = io.StringIO(newline="")
            writer = csv.DictWriter(content, fieldnames=headers)
            writer.writeheader()
            writer.writerows({key: _safe(row.get(key, "")) for key in headers} for row in rows)
            archive.writestr(filename, content.getvalue())
    return output.getvalue()


def gexf(request: GraphExportRequest) -> bytes:
    graph = build_graph(request)
    namespace = "http://www.gexf.net/1.2draft"
    etree.register_namespace("", namespace)
    root = etree.Element(f"{{{namespace}}}gexf", version="1.2")
    network = etree.SubElement(root, f"{{{namespace}}}graph", defaultedgetype="directed", mode="static")
    node_attributes = etree.SubElement(network, f"{{{namespace}}}attributes", {"class": "node"})
    for index, name in enumerate(("type", "platform", "url", "confidence")):
        etree.SubElement(node_attributes, f"{{{namespace}}}attribute", id=str(index), title=name, type="string")
    nodes = etree.SubElement(network, f"{{{namespace}}}nodes")
    for item in graph.nodes:
        node = etree.SubElement(nodes, f"{{{namespace}}}node", id=item["Id"], label=item["Label"])
        values = etree.SubElement(node, f"{{{namespace}}}attvalues")
        for index, name in enumerate(("Type", "Platform", "URL", "Confidence")):
            etree.SubElement(values, f"{{{namespace}}}attvalue", {"for": str(index), "value": item[name]})
    edges = etree.SubElement(network, f"{{{namespace}}}edges")
    for index, item in enumerate(graph.edges):
        etree.SubElement(edges, f"{{{namespace}}}edge", id=str(index), source=item["Source"], target=item["Target"], label=item["Label"], weight=item["Weight"])
    return etree.tostring(root, encoding="utf-8", xml_declaration=True)
