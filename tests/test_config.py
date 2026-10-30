from claude_usage_smalltv.config import Config, load_config, save_config


def test_round_trip(tmp_path):
    path = tmp_path / "sub" / "config.json"
    save_config(Config(host="10.0.0.9", lang="pt"), path)
    assert load_config(path) == Config(host="10.0.0.9", lang="pt", usage_interval=300)


def test_missing_or_broken_file_falls_back_to_defaults(tmp_path):
    assert load_config(tmp_path / "nope.json") == Config()
    broken = tmp_path / "config.json"
    broken.write_text("{not json", encoding="utf-8")
    assert load_config(broken) == Config()


def test_unknown_keys_from_newer_versions_are_ignored(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"host": "x", "theme": "neon"}', encoding="utf-8")
    assert load_config(path) == Config(host="x")
