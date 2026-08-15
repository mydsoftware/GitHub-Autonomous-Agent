# GitHub Autonomous Agent

Autonomous software engineering agent running through GitHub Actions.

## Goal

Receive a natural-language software request, plan it, implement it, test it, repair failures, commit the result, and optionally deploy it.

## Architecture

- GitHub Issues / workflow dispatch: task input
- GitHub Actions: execution loop
- AI provider: planning and coding
- Repository workspace: generated project
- Tests/build: validation and self-repair
- GitHub Pages / deployment target: optional delivery

## Current status

Bootstrap phase. The next steps add the agent runtime, task intake workflow, configuration, safe execution loop, and delivery reporting.
