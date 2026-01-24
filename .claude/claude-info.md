# Additional Capabilities You Can Enable

```
  Custom commands & aliases - Define project-specific commands:
  {
    "commands": {
      "test": "pytest tests/",
      "lint": "ruff check .",
      "deploy": "python deploy.py"
    }
  }

  Tool permissions - Pre-approve specific tools:
  {
    "permissions": {
      "allow": [
        "Bash(npm:*)",
        "Bash(git:*)",
        "Write",
        "Edit"
      ]
    }
  }

  Environment variables - Set project context:
  {
    "env": {
      "PROJECT_TYPE": "python",
      "TEST_FRAMEWORK": "pytest"
    }
  }

  Hooks - Trigger actions on events:
  {
    "hooks": {
      "before_edit": "python format_check.py",
      "after_write": "python validate.py"
    }
  }
```
