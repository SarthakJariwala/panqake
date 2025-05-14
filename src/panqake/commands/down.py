"""Command for navigating to child branch in stack."""

import sys

from panqake.utils.git import checkout_branch, get_current_branch
from panqake.utils.questionary_prompt import print_formatted_text, prompt_select
from panqake.utils.stack import Stacks


def down():
    """Navigate to a child branch in the stack.
    
    If the current branch has:
    - No children: Informs the user and exits
    - One child: Directly switches to that child branch
    - Multiple children: Prompts user to select which child to navigate to
    """
    current_branch = get_current_branch()
    
    # Get the child branches using the Stacks utility
    with Stacks() as stacks:
        children = stacks.get_children(current_branch)
        
        if not children:
            print_formatted_text(
                f"[warning]Branch '{current_branch}' has no child branches[/warning]"
            )
            sys.exit(1)
        
        # If there's only one child, switch directly
        if len(children) == 1:
            child = children[0]
            print_formatted_text(f"[info]Moving down to child branch: '{child}'[/info]")
            checkout_branch(child)
            return
        
        # Multiple children, prompt for selection
        print_formatted_text(f"[info]Branch '{current_branch}' has multiple children[/info]")
        
        # Format child branches for display
        choices = []
        for child in children:
            child_item = {"display": child, "value": child}
            choices.append(child_item)
        
        # Show interactive branch selection
        selected = prompt_select(
            "Select a child branch to switch to:",
            choices,
        )
        
        if selected:
            print_formatted_text(f"[info]Moving down to child branch: '{selected}'[/info]")
            checkout_branch(selected)