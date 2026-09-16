import json

import pytest

from llm_agent.tool_filesystem import FileSystemTool


@pytest.fixture
def tool(tmp_path):
    return FileSystemTool(sandbox_dir=tmp_path / "sandbox")


def test_write_and_read(tool):
    tool.write("notes/hello.txt", "Привет, мир")
    assert tool.read("notes/hello.txt") == "Привет, мир"


def test_list(tool):
    assert tool.list() == "Директория пуста."
    tool.write("a.txt", "1")
    tool.write("sub/b.txt", "2")
    assert tool.list() == "[FILE] a.txt\n[DIR] sub"


def test_delete(tool):
    tool.write("tmp.txt", "x")
    tool.delete("tmp.txt")
    assert tool.list() == "Директория пуста."
    with pytest.raises(FileNotFoundError):
        tool.delete("tmp.txt")


@pytest.mark.parametrize("bad_path", ["../outside.txt", "/etc/passwd", "sub/../../x.txt", ""])
def test_sandbox_escape_blocked(tool, bad_path):
    with pytest.raises(ValueError):
        tool.read(bad_path)
    with pytest.raises(ValueError):
        tool.write(bad_path, "hack")


def test_use_dict_and_json(tool):
    assert "успешно записан" in tool.use({"operation": "write", "path": "doc.txt", "content": "текст"})
    assert tool.use(json.dumps({"operation": "read", "path": "doc.txt"})) == "текст"
    assert tool.use('{"operation": "list"}') == "[FILE] doc.txt"
    assert "успешно удалён" in tool.use({"operation": "delete", "path": "doc.txt"})


def test_use_errors(tool):
    assert tool.use("not json").startswith("Ошибка FileSystemTool")
    assert tool.use({"operation": "rename", "path": "a"}).startswith("Ошибка FileSystemTool")
    assert tool.use({"operation": "read", "path": "../../etc/passwd"}).startswith("Ошибка FileSystemTool")
    assert tool.use({"operation": "read", "path": "missing.txt"}).startswith("Ошибка FileSystemTool")
    assert tool.use({"operation": "write", "path": "a.txt"}).startswith("Ошибка FileSystemTool")
