import json
from pathlib import Path
import pytest
from freeswitch.agent import tool_list_directory, tool_read_file, tool_write_file, tool_edit_file


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
