"""Tests for questionary_prompt.py module."""

from unittest.mock import Mock, patch

import pytest
from questionary import ValidationError

from panqake.utils.questionary_prompt import (
    BranchNameValidator,
    PRTitleValidator,
    format_branch,
    print_formatted_text,
    prompt_checkbox,
    prompt_confirm,
    prompt_for_parent,
    prompt_input,
    prompt_select,
    rich_prompt,
)


@pytest.fixture
def mock_console():
    """Mock rich console for testing."""
    with patch("panqake.utils.questionary_prompt.console") as mock:
        yield mock


@pytest.fixture
def mock_questionary():
    """Mock questionary for testing."""
    with patch("questionary.text") as mock_text:
        with patch("questionary.confirm") as mock_confirm:
            with patch("questionary.checkbox") as mock_checkbox:
                with patch("questionary.select") as mock_select:
                    with patch("questionary.autocomplete") as mock_autocomplete:
                        mock_text.return_value.ask.return_value = "test input"
                        mock_confirm.return_value.ask.return_value = True
                        mock_checkbox.return_value.ask.return_value = [
                            "item1",
                            "item2",
                        ]
                        mock_select.return_value.ask.return_value = "selected"
                        mock_autocomplete.return_value.ask.return_value = (
                            "autocompleted"
                        )
                        yield {
                            "text": mock_text,
                            "confirm": mock_confirm,
                            "checkbox": mock_checkbox,
                            "select": mock_select,
                            "autocomplete": mock_autocomplete,
                        }


def test_format_branch_normal():
    """Test formatting a normal branch name."""
    result = format_branch("main")
    assert result == "main"


def test_format_branch_current():
    """Test formatting current branch name."""
    result = format_branch("main", current=True)
    assert result == "[branch]* main[/branch]"


def test_format_branch_danger():
    """Test formatting branch name with danger style."""
    result = format_branch("main", danger=True)
    assert result == "[danger]main[/danger]"


def test_print_formatted_text(mock_console):
    """Test printing formatted text."""
    print_formatted_text("[info]test message[/info]")
    mock_console.print.assert_called_once_with("[info]test message[/info]", markup=True)


def test_rich_prompt(mock_console):
    """Test rich prompt display."""
    rich_prompt("test message")
    mock_console.print.assert_called_once_with("[prompt]test message[/prompt]")


def test_prompt_input_basic(mock_questionary):
    """Test basic text input prompt."""
    result = prompt_input("Enter value:")
    mock_questionary["text"].assert_called_once()
    assert result == "test input"


def test_prompt_input_with_autocomplete(mock_questionary):
    """Test input prompt with autocomplete."""
    result = prompt_input("Select:", completer=["option1", "option2"])
    mock_questionary["autocomplete"].assert_called_once()
    assert result == "autocompleted"


def test_prompt_confirm(mock_questionary):
    """Test confirmation prompt."""
    result = prompt_confirm("Proceed?")
    mock_questionary["confirm"].assert_called_once()
    assert result is True


def test_prompt_checkbox(mock_questionary):
    """Test checkbox selection prompt."""
    choices = ["item1", "item2", "item3"]
    result = prompt_checkbox("Select items:", choices)
    mock_questionary["checkbox"].assert_called_once()
    assert result == ["item1", "item2"]


def test_prompt_checkbox_with_dict_choices(mock_questionary):
    """Test checkbox selection with dictionary choices."""
    choices = [
        {"display": "Item 1", "path": "item1"},
        {"display": "Item 2", "path": "item2"},
    ]
    result = prompt_checkbox("Select items:", choices)
    mock_questionary["checkbox"].assert_called_once()
    assert result == ["item1", "item2"]


def test_prompt_select(mock_questionary):
    """Test single selection prompt."""
    choices = ["option1", "option2"]
    result = prompt_select("Select one:", choices)
    mock_questionary["select"].assert_called_once()
    assert result == "selected"


def test_prompt_select_with_dict_choices(mock_questionary):
    """Test single selection with dictionary choices."""
    choices = [
        {"display": "Option 1", "value": "opt1"},
        {"display": "Option 2", "value": "opt2", "disabled": True},
    ]
    result = prompt_select("Select one:", choices)
    mock_questionary["select"].assert_called_once()
    assert result == "selected"


def test_prompt_for_parent(mock_questionary):
    """Test parent branch selection prompt."""
    branches = ["main", "develop", "feature"]
    result = prompt_for_parent(branches)
    mock_questionary["select"].assert_called_once()
    assert result == "selected"


def test_prompt_for_parent_empty_list():
    """Test parent branch selection with empty list."""
    result = prompt_for_parent([])
    assert result is None


def test_branch_name_validator_valid():
    """Test branch name validator with valid input."""
    validator = BranchNameValidator()
    document = Mock()
    document.text = "feature-branch"
    validator.validate(document)  # Should not raise ValidationError


def test_branch_name_validator_empty():
    """Test branch name validator with empty input."""
    validator = BranchNameValidator()
    document = Mock()
    document.text = ""
    with pytest.raises(ValidationError, match="Branch name cannot be empty"):
        validator.validate(document)


def test_branch_name_validator_invalid_space():
    """Test branch name validator with spaces."""
    validator = BranchNameValidator()
    document = Mock()
    document.text = "feature branch"
    with pytest.raises(ValidationError, match="Branch name cannot contain spaces"):
        validator.validate(document)


def test_pr_title_validator_valid():
    """Test PR title validator with valid input."""
    validator = PRTitleValidator()
    document = Mock()
    document.text = "Add new feature for user authentication"
    validator.validate(document)  # Should not raise ValidationError


def test_pr_title_validator_empty():
    """Test PR title validator with empty input."""
    validator = PRTitleValidator()
    document = Mock()
    document.text = ""
    with pytest.raises(ValidationError, match="PR title cannot be empty"):
        validator.validate(document)


def test_pr_title_validator_too_short():
    """Test PR title validator with short input."""
    validator = PRTitleValidator()
    document = Mock()
    document.text = "Fix bug"
    with pytest.raises(
        ValidationError, match="PR title should be at least 10 characters"
    ):
        validator.validate(document)
