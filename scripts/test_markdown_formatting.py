#!/usr/bin/env python3
"""
Script to test and demonstrate Markdown formatting utilities.

This script showcases the capabilities of the Markdown utilities
for problem content formatting in the Daily Challenge application.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)

from app.utils.markdown_utils import (
    get_markdown_css,
    markdown_preview,
    markdown_to_html,
    truncate_markdown
)

EXAMPLE_MARKDOWN = """
# Python Binary Tree Traversal Challenge

Given a binary tree, implement the three standard traversal methods:
1. Pre-order traversal
2. In-order traversal
3. Post-order traversal

## Problem Description

A binary tree is represented by a `TreeNode` class:

```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

Implement the following functions:

```python
def preorder_traversal(root):
    \"\"\"Return the pre-order traversal of the tree's values.\"\"\"
    # Your code here
    pass

def inorder_traversal(root):
    \"\"\"Return the in-order traversal of the tree's values.\"\"\"
    # Your code here
    pass

def postorder_traversal(root):
    \"\"\"Return the post-order traversal of the tree's values.\"\"\"
    # Your code here
    pass
```

## Example

For the following binary tree:

```
    1
   / \\
  2   3
 / \\
4   5
```

* Pre-order traversal: `[1, 2, 4, 5, 3]`
* In-order traversal: `[4, 2, 5, 1, 3]`
* Post-order traversal: `[4, 5, 2, 3, 1]`

## Solution

<details>
<summary>Click to reveal solution</summary>

Here's a recursive implementation of the three traversal methods:

```python
def preorder_traversal(root):
    if not root:
        return []
    
    result = [root.val]
    result.extend(preorder_traversal(root.left))
    result.extend(preorder_traversal(root.right))
    return result

def inorder_traversal(root):
    if not root:
        return []
    
    result = inorder_traversal(root.left)
    result.append(root.val)
    result.extend(inorder_traversal(root.right))
    return result

def postorder_traversal(root):
    if not root:
        return []
    
    result = postorder_traversal(root.left)
    result.extend(postorder_traversal(root.right))
    result.append(root.val)
    return result
```

Non-recursive implementations using a stack are also possible for each traversal method.
</details>
"""

def write_html_preview(filename: str, markdown: str) -> str:
    """Generate an HTML preview file from Markdown content."""
    preview = markdown_preview(markdown)
    
    # Create HTML document with CSS and content
    html = "\n".join([
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "    <meta charset=\"UTF-8\">",
        "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        "    <title>Markdown Preview</title>",
        "    <style>",
        preview['css'],
        "    </style>",
        "</head>",
        "<body class=\"markdown-body\">",
        preview['toc_html'],
        "    <hr>",
        preview['html'],
        "</body>",
        "</html>"
    ])
    
    with open(filename, 'w') as f:
        f.write(html)
    
    return filename

def main() -> None:
    """Run the demonstration of Markdown formatting utilities."""
    print("\n=== Markdown Formatting Utilities Demonstration ===\n")
    
    # 1. Basic HTML conversion with syntax highlighting
    print("1. Basic Markdown to HTML conversion:")
    html = markdown_to_html(EXAMPLE_MARKDOWN)
    print(f"  Converted {len(EXAMPLE_MARKDOWN)} chars of Markdown to "
          f"{len(html)} chars of HTML")
    
    # 2. Complete preview with TOC and CSS
    print("\n2. Complete Markdown preview with table of contents:")
    preview = markdown_preview(EXAMPLE_MARKDOWN)
    print(f"  Generated {len(preview['html'])} chars of HTML")
    print(f"  Generated {len(preview['toc_html'])} chars of TOC HTML")
    print(f"  Generated {len(preview['css'])} chars of CSS")
    
    # 3. Truncate Markdown for summary display
    print("\n3. Truncated Markdown for summary display:")
    truncated = truncate_markdown(EXAMPLE_MARKDOWN, 100)
    print(f"  Original length: {len(EXAMPLE_MARKDOWN)}")
    print(f"  Truncated length: {len(truncated)}")
    print(f"  Truncated preview: {truncated}")
    
    # 4. Write an HTML preview file
    output_file = write_html_preview(
        "markdown_preview_example.html", 
        EXAMPLE_MARKDOWN
    )
    print(f"\n4. Generated HTML preview file: {os.path.abspath(output_file)}")
    print("  Open this file in a web browser to see the formatted content")
    
    print("\n=== End of Demonstration ===")

if __name__ == "__main__":
    main()
