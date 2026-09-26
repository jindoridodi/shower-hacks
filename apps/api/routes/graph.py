"""Gephi-compatible graph download route."""

from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response

from apps.api.services.graph.gephi import csv_zip, gexf
from apps.api.services.graph.models import GraphExportRequest

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.post("/export")
async def export_graph(request: GraphExportRequest, format: Literal["csv", "gexf"] = Query("csv")) -> Response:
    if format == "csv":
        return Response(csv_zip(request), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=discovery-graph.zip"})
    return Response(gexf(request), media_type="application/gexf+xml", headers={"Content-Disposition": "attachment; filename=discovery-graph.gexf"})
