"""Tests for the freeswitch model registry and config."""

from freeswitch import models, config


def test_list_models_returns_entries():
    result = models.list_models()
    assert len(result) > 0
    assert all("alias" in m and "provider" in m for m in result)


def test_list_models_has_description():
    result = models.list_models()
    assert all("description" in m for m in result)


def test_get_model_known_alias():
    info = models.get_model("nemotron-ultra")
    assert info["provider"] == "openrouter"
    assert info["free"] is True
    assert "nvidia" in info["model"].lower()


def test_get_model_unknown_raises():
    try:
        models.get_model("does-not-exist")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_default_active_is_valid():
    active = config.get_active()
    assert models.get_model(active)


def test_all_free_models_have_free_tag():
    for m in models.list_models():
        if m["free"] and m["provider"] == "openrouter" and m["model"] != "openrouter/free":
            assert ":free" in m["model"], \
                f"{m['alias']} is marked free but model ID has no :free suffix"


def test_all_models_have_api_base():
    for alias, info in models.MODELS.items():
        assert "api_base" in info, f"{alias} missing api_base"
        assert info["api_base"].startswith("http"), f"{alias} has invalid api_base"


def test_default_model_exists():
    assert models.DEFAULT_MODEL in models.MODELS
