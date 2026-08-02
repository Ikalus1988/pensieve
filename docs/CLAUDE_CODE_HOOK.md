# Claude Code hook setup

Example `UserPromptSubmit` hook command:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "pensieve hook \"$PROMPT\" --cwd \"$PWD\""
          }
        ]
      }
    ]
  }
}
```

Adjust to the exact environment variables provided by your Claude Code hook runtime. The command must print either `{}` or a JSON object with `hookSpecificOutput.additionalContext`.

Pensieve intentionally injects only a short pointer to the routine card. The agent should load the card only if needed.
