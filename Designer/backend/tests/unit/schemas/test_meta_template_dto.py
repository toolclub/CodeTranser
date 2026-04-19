import pytest
from pydantic import ValidationError

from app.schemas.meta_template import MetaTemplateDTO, MetaTemplateFieldDTO


def test_valid_meta_template() -> None:
    t = MetaTemplateDTO(
        version=1,
        fields=[MetaTemplateFieldDTO(key="name", label="n", type="string", required=True)],
    )
    assert t.fields[0].type == "string"


def test_invalid_field_type_rejected() -> None:
    with pytest.raises(ValidationError):
        MetaTemplateFieldDTO(key="x", label="x", type="invalid_type")  # type: ignore[arg-type]
