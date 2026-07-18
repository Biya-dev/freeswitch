import json
from pathlib import Path
import pytest
from freeswitch.agent import tool_list_directory, tool_read_file, tool_write_file, tool_edit_file, tool_search_code, is_outside_workspace


def test_agent_file_tools(tmp_path):
    # Setup test file
    test_file = tmp_path / "hello.txt"
    
    # 1. Test write
    res = tool_write_file(str(test_file), "Hello World\nLine 2\nLine 3")
    assert "success" in res
    assert test_file.read_text(encoding="utf-8") == "Hello World\nLine 2\nLine 3"
    
    # 2. Test read
    content = tool_read_file(str(test_file))
    assert "Hello World" in content
    
    # 3. Test list
    list_res = json.loads(tool_list_directory(str(tmp_path)))
    assert list_res["status"] == "success"
    assert "hello.txt" in list_res["contents"]

    # 4. Test edit (success case)
    edit_res = json.loads(tool_edit_file(str(test_file), "Line 2", "Line Two"))
    assert edit_res["status"] == "success"
    assert test_file.read_text(encoding="utf-8") == "Hello World\nLine Two\nLine 3"

    # 5. Test edit (failure case: content not found)
    edit_res2 = json.loads(tool_edit_file(str(test_file), "Nonexistent Line", "No change"))
    assert edit_res2["status"] == "error"
    assert "Could not find" in edit_res2["message"]


def test_agent_search_code(tmp_path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello World\nPython Agent\nCode Search Test", encoding="utf-8")
    
    # 1. Test query found
    res = json.loads(tool_search_code("agent", str(tmp_path)))
    assert res["status"] == "success"
    assert len(res["matches"]) == 1
    assert "Python Agent" in res["matches"][0]
    
    # 2. Test query not found
    res2 = json.loads(tool_search_code("nonexistent", str(tmp_path)))
    assert res2["status"] == "success"
    assert "No matches found" in res2["message"]


def test_is_outside_workspace(tmp_path):
    # Within workspace
    assert is_outside_workspace(str(Path.cwd())) is False
    assert is_outside_workspace(str(Path.cwd() / "freeswitch")) is False
    
    # Outside workspace
    assert is_outside_workspace(str(tmp_path)) is True
    assert is_outside_workspace(None) is False


def test_run_agent_loop_with_failing_test_command(monkeypatch):
    import requests
    from freeswitch import agent
    
    monkeypatch.setattr(agent, "get_model", lambda alias: {
        "provider": "openrouter",
        "model": "nvidia/llama-3.1-nemotron-ultra-253b:free",
        "api_base": "https://openrouter.ai/api/v1"
    })
    monkeypatch.setattr(agent, "get_key", lambda provider: "fake_key")
    monkeypatch.setattr(agent, "offer_git_commit", lambda alias: None)
    
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self.json_data = json_data
            self.status_code = status_code
        def json(self):
            return self.json_data
        def raise_for_status(self):
            pass
            
    call_count = 0
    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            raise KeyboardInterrupt("Stop test")
        return MockResponse({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": f"Attempt {call_count}",
                    "tool_calls": None
                }
            }]
        })
        
    monkeypatch.setattr(requests, "post", mock_post)
    
    try:
        agent.run_agent_loop("nemotron-ultra", "test task", test_command="python -c \"import sys; sys.exit(1)\"")
    except KeyboardInterrupt:
        pass
        
    assert call_count == 3
