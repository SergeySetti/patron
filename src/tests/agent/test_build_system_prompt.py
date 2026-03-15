from agents.patron_itself.patron_agent import _build_system_prompt


class TestBuildSystemPrompt:

    def test_without_custom_prompt(self):
        result = _build_system_prompt("Europe/Kyiv")

        assert "Europe/Kyiv" in result
        assert "User instructions" not in result

    def test_with_custom_prompt(self):
        result = _build_system_prompt("Europe/Kyiv", "Always reply in Ukrainian")

        assert "Europe/Kyiv" in result
        assert "User instructions:" in result
        assert "Always reply in Ukrainian" in result

    def test_empty_custom_prompt_not_included(self):
        result = _build_system_prompt("Europe/Kyiv", "")

        assert "User instructions" not in result

    def test_no_timezone_with_custom_prompt(self):
        result = _build_system_prompt("", "Be concise")

        assert "do not know the user's timezone" in result
        assert "Be concise" in result
