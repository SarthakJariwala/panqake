"""Tests for selection utility functions."""

from unittest.mock import patch


from panqake.utils.selection import (
    select_branch_excluding_current,
    select_files_for_staging,
    select_from_options,
    select_multiple_from_options,
    select_parent_branch,
    select_reviewers,
)


class TestSelectBranchExcludingCurrent:
    """Tests for select_branch_excluding_current function."""

    @patch("panqake.utils.selection.prompt_select")
    @patch("panqake.utils.selection.get_current_branch")
    @patch("panqake.utils.selection.list_all_branches")
    def test_select_branch_excluding_current_success(
        self, mock_list_branches, mock_current_branch, mock_prompt_select
    ):
        """Test successful branch selection excluding current."""
        mock_list_branches.return_value = ["main", "feature1", "feature2"]
        mock_current_branch.return_value = "feature1"
        mock_prompt_select.return_value = "feature2"

        result = select_branch_excluding_current()

        assert result == "feature2"
        mock_prompt_select.assert_called_once()
        call_args = mock_prompt_select.call_args
        choices = call_args[0][1]  # Second positional argument
        # Should exclude current branch and main (protected)
        assert len(choices) == 1
        assert choices[0]["value"] == "feature2"

    @patch("panqake.utils.selection.get_current_branch")
    @patch("panqake.utils.selection.list_all_branches")
    def test_select_branch_excluding_current_no_branches(
        self, mock_list_branches, mock_current_branch
    ):
        """Test when no branches are available."""
        mock_list_branches.return_value = []
        mock_current_branch.return_value = "main"

        result = select_branch_excluding_current()

        assert result is None

    @patch("panqake.utils.selection.get_current_branch")
    @patch("panqake.utils.selection.list_all_branches")
    def test_select_branch_excluding_current_no_available_after_filter(
        self, mock_list_branches, mock_current_branch
    ):
        """Test when no branches available after filtering."""
        mock_list_branches.return_value = ["main", "feature1"]
        mock_current_branch.return_value = "feature1"

        result = select_branch_excluding_current()

        assert result is None


class TestSelectParentBranch:
    """Tests for select_parent_branch function."""

    @patch("panqake.utils.selection.prompt_for_parent")
    def test_select_parent_branch_success(self, mock_prompt_for_parent):
        """Test successful parent branch selection."""
        potential_parents = ["main", "develop"]
        mock_prompt_for_parent.return_value = "main"

        result = select_parent_branch(potential_parents)

        assert result == "main"
        mock_prompt_for_parent.assert_called_once_with(potential_parents)

    def test_select_parent_branch_empty_list(self):
        """Test with empty list of potential parents."""
        result = select_parent_branch([])

        assert result is None


class TestSelectFilesForStaging:
    """Tests for select_files_for_staging function."""

    @patch("panqake.utils.selection.prompt_checkbox")
    def test_select_files_for_staging_success(self, mock_prompt_checkbox):
        """Test successful file selection."""
        files = [
            {"display": "file1.py", "path": "file1.py"},
            {"display": "file2.py", "path": "file2.py"},
        ]
        mock_prompt_checkbox.return_value = ["file1.py"]

        result = select_files_for_staging(files)

        assert result == ["file1.py"]
        mock_prompt_checkbox.assert_called_once()

    def test_select_files_for_staging_empty_list(self):
        """Test with empty file list."""
        result = select_files_for_staging([])

        assert result == []


class TestSelectReviewers:
    """Tests for select_reviewers function."""

    @patch("panqake.utils.selection.prompt_checkbox")
    def test_select_reviewers_success(self, mock_prompt_checkbox):
        """Test successful reviewer selection."""
        potential_reviewers = ["user1", "user2", "user3"]
        mock_prompt_checkbox.return_value = ["user1", "user3"]

        result = select_reviewers(potential_reviewers)

        assert result == ["user1", "user3"]
        mock_prompt_checkbox.assert_called_once()

    @patch("panqake.utils.selection.prompt_checkbox")
    def test_select_reviewers_with_skip_option(self, mock_prompt_checkbox):
        """Test reviewer selection with skip option."""
        potential_reviewers = ["user1", "user2"]
        mock_prompt_checkbox.return_value = ["", "user1"]  # Including empty value

        result = select_reviewers(potential_reviewers, include_skip_option=True)

        assert result == ["user1"]  # Empty values should be filtered out

    def test_select_reviewers_empty_list(self):
        """Test with empty reviewer list."""
        result = select_reviewers([])

        assert result == []


class TestSelectFromOptions:
    """Tests for select_from_options function."""

    @patch("panqake.utils.selection.prompt_select")
    def test_select_from_options_success(self, mock_prompt_select):
        """Test successful option selection."""
        options = ["option1", "option2", "option3"]
        mock_prompt_select.return_value = "option2"

        result = select_from_options(options)

        assert result == "option2"
        mock_prompt_select.assert_called_once()

    def test_select_from_options_empty_list(self):
        """Test with empty options list."""
        result = select_from_options([])

        assert result is None


class TestSelectMultipleFromOptions:
    """Tests for select_multiple_from_options function."""

    @patch("panqake.utils.selection.prompt_checkbox")
    def test_select_multiple_from_options_success(self, mock_prompt_checkbox):
        """Test successful multiple option selection."""
        options = ["option1", "option2", "option3"]
        mock_prompt_checkbox.return_value = ["option1", "option3"]

        result = select_multiple_from_options(options)

        assert result == ["option1", "option3"]
        mock_prompt_checkbox.assert_called_once()

    def test_select_multiple_from_options_empty_list(self):
        """Test with empty options list."""
        result = select_multiple_from_options([])

        assert result == []
