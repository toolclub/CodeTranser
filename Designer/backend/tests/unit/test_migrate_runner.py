from app.infra.migrate.runner import split_statements


def test_split_ignores_line_comments() -> None:
    sql = """
-- some comment
CREATE TABLE a (id INT);
-- another
CREATE TABLE b (id INT);
"""
    stmts = split_statements(sql)
    assert len(stmts) == 2
    assert "CREATE TABLE a" in stmts[0]
    assert "CREATE TABLE b" in stmts[1]


def test_split_multiline_statement() -> None:
    sql = """
CREATE TABLE multi (
  id INT PRIMARY KEY,
  name VARCHAR(32)
);
"""
    stmts = split_statements(sql)
    assert len(stmts) == 1
    assert "VARCHAR(32)" in stmts[0]


def test_split_no_trailing_semicolon() -> None:
    sql = "SELECT 1"
    stmts = split_statements(sql)
    assert stmts == ["SELECT 1"]
