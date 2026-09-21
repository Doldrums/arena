"""Stable read-only research-tool observer API.

Record projections, job status, immutable artifacts and cell evidence live in
separate modules. Public schemas and journal provenance retain their native names.
"""
from .research_tool_records import (
    EVENT_SCHEMA,
    HASH,
    LIMIT,
    DETAIL_LIMIT,
    DETAIL_BYTES,
    _obj,
    _text,
    _island,
    _ids,
    _events,
    _canonical,
    _job_number,
    _compact,
    _research_state,
    _background_transfer,
    _method_trial,
)
from .research_tool_jobs import (
    _job_bindings,
    _job_base,
    _bound_job,
    _job_row,
    BackgroundJobView,
    job_detail,
)
from .research_cell_state import (
    _continuations,
    _sharing,
    _cells_view,
    _configuration,
    _cell_events,
    _committed_followups,
    _enrich_cells,
)
from .research_tool_projection import (
    research_tools_view,
)
from .research_tool_artifacts import (
    _read_object,
    _bundle,
    tool_detail,
    artifact_detail,
    _comparison_assessment,
    _candidate_evaluation_detail,
    _DetailReader,
)
from .research_cell_detail import (
    _cell_followup,
    _terminal_decision,
    _cell_related,
    cell_detail,
)
