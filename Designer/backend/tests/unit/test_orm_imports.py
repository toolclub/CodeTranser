from app.infra.db.base import Base
from app.models.mysql import (
    AdminUserRow,
    AppSettingRow,
    AuditLogRow,
    CascadeGraphRow,
    CodeSnapshotRow,
    GraphDraftRow,
    GraphReviewRow,
    GraphVersionRow,
    JsonCaseRow,
    MetaTemplateRow,
    MigrationAppliedRow,
    NodeTemplateRow,
    NodeTemplateVersionRow,
    ReviewCommentRow,
    RunStepRow,
    SandboxCaseRow,
    UserRow,
    WorkflowRunRow,
)

EXPECTED_TABLES = {
    "t_migration_applied",
    "t_user",
    "t_admin_user",
    "t_meta_node_template",
    "t_node_template",
    "t_node_template_version",
    "t_cascade_graph",
    "t_graph_version",
    "t_graph_draft",
    "t_workflow_run",
    "t_run_step",
    "t_json_case",
    "t_sandbox_case",
    "t_code_snapshot",
    "t_graph_review",
    "t_review_comment",
    "t_audit_log",
    "t_app_setting",
}

ROW_CLASSES = [
    MigrationAppliedRow,
    UserRow,
    AdminUserRow,
    MetaTemplateRow,
    NodeTemplateRow,
    NodeTemplateVersionRow,
    CascadeGraphRow,
    GraphVersionRow,
    GraphDraftRow,
    WorkflowRunRow,
    RunStepRow,
    JsonCaseRow,
    SandboxCaseRow,
    CodeSnapshotRow,
    GraphReviewRow,
    ReviewCommentRow,
    AuditLogRow,
    AppSettingRow,
]


def test_row_classes_cover_all_tables() -> None:
    table_names = {cls.__tablename__ for cls in ROW_CLASSES}
    assert table_names == EXPECTED_TABLES


def test_base_metadata_has_all_tables() -> None:
    registered = set(Base.metadata.tables.keys())
    assert EXPECTED_TABLES.issubset(registered)
