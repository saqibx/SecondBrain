import pytest

from secondbrain.loaders import clean_text, discover_files, is_supported, load_file


def test_load_txt(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello world")
    assert load_file(f) == "hello world"


def test_load_markdown(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("# Title\n\nbody")
    assert "Title" in load_file(f)


def test_load_html_strips_tags(tmp_path):
    f = tmp_path / "page.html"
    f.write_text("<html><head><script>var x=1;</script></head><body><p>visible text</p></body></html>")
    text = load_file(f)
    assert "visible text" in text
    assert "var x" not in text


def test_load_json(tmp_path):
    f = tmp_path / "data.json"
    f.write_text('{"key": "value"}')
    assert "value" in load_file(f)


def test_unsupported_extension(tmp_path):
    f = tmp_path / "image.png"
    f.write_bytes(b"\x89PNG")
    assert not is_supported(f)
    with pytest.raises(ValueError):
        load_file(f)


def test_discover_files_recursive(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.md").write_text("b")
    (tmp_path / "sub" / "c.png").write_bytes(b"x")
    (tmp_path / ".hidden.txt").write_text("h")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "d.txt").write_text("d")

    found = {p.name for p in discover_files(tmp_path)}
    assert found == {"a.txt", "b.md"}


def test_discover_single_file(tmp_path):
    f = tmp_path / "one.txt"
    f.write_text("x")
    assert discover_files(f) == [f]


def test_clean_text():
    assert clean_text("a\r\nb\n\n\n\nc   d") == "a\nb\n\nc d"
