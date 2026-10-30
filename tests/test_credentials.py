import json

import pytest

from claude_usage_smalltv import credentials
from claude_usage_smalltv.credentials import CredentialsError, load_token, parse_credentials

STORED = {
    "claudeAiOauth": {
        "accessToken": "sk-ant-oat-test",
        "refreshToken": "never-read",
        "expiresAt": 1_900_000_000_000,
        "subscriptionType": "max",
    }
}


def test_parse_credentials_converts_ms_to_seconds():
    tok = parse_credentials(json.dumps(STORED))
    assert tok.access_token == "sk-ant-oat-test"
    assert tok.expires_at == 1_900_000_000
    assert tok.plan == "max"


@pytest.mark.parametrize("raw", ["not json", "{}", '{"claudeAiOauth": {}}'])
def test_parse_credentials_rejects_unexpected_formats(raw):
    with pytest.raises(CredentialsError):
        parse_credentials(raw)


def test_load_token_reads_claude_config_dir(tmp_path, monkeypatch):
    (tmp_path / ".credentials.json").write_text(json.dumps(STORED), encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    assert load_token().plan == "max"


def test_load_token_explains_how_to_sign_in(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(credentials, "_read_keychain", lambda: None)
    with pytest.raises(CredentialsError, match="run `claude`"):
        load_token()


def test_renew_token_without_cli_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(credentials, "find_claude_cli", lambda: None)
    with pytest.raises(CredentialsError, match="not found"):
        credentials.renew_token()
