from app.domain.tool.tool import (
    CodeGenerationHints,
    EdgeSemantic,
    Engine,
    JsonSimulatorSpec,
    NodeTemplate,
    Scope,
)

# 向后兼容别名(设计文档里 Tool = NodeTemplate)
Tool = NodeTemplate

__all__ = [
    "CodeGenerationHints",
    "EdgeSemantic",
    "Engine",
    "JsonSimulatorSpec",
    "NodeTemplate",
    "Scope",
    "Tool",
]
