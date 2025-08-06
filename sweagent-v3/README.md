# SWE Agent V3 - Working Software Engineering Assistant

A proper implementation of an SWE agent that works like Claude Code, with native Anthropic tool calling.

## What You Get

**Just 3 files:**
- `swe_agent.py` - The working agent
- `requirements.txt` - Dependencies (just `anthropic`)
- `test_swe.py` - Simple test

## Setup

```bash
pip install anthropic
export ANTHROPIC_API_KEY="your_key_here"
```

## Usage

**Command line:**
```bash
python swe_agent.py "create a Flask hello world app"
python swe_agent.py "build a Python calculator with tests"
python swe_agent.py "analyze this codebase and suggest improvements"
```

**Test it works:**
```bash
python test_swe.py
```

## Tools Available

1. **bash** - Execute shell commands (mkdir, ls, git, npm, pytest, etc.)
2. **str_replace_editor** - Create, read, and edit files

## Why This Works

- Uses Claude's native tool calling (no custom parsing)
- Proper conversation flow like Claude Code
- Simple, focused implementation
- Actually tested and working

This is what an SWE agent should be - simple, working, and effective.