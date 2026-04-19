from app.domain.graph.errors import FieldValueInvalid
from app.domain.graph.nodes import NodeInstance
from app.domain.graph.visitor import ForestVisitor
from app.tool_runtime.errors import SimulatorInputInvalid
from app.tool_runtime.json_schema import validate_input


class SchemaValidationVisitor(ForestVisitor):
    """每个 NodeInstance 的 field_values 必须符合其 template.input_schema。"""

    def visit_node(self, n: NodeInstance) -> None:
        try:
            validate_input(n.template_snapshot.input_schema, dict(n.field_values))
        except SimulatorInputInvalid as e:
            raise FieldValueInvalid(
                str(e),
                instance_id=n.instance_id,
                template=n.template_snapshot.name,
            ) from e
