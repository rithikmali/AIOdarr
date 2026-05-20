# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---
## [LRN-20260520-001] correction

**Logged**: 2026-05-20T13:29:51Z
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Do not assume third-party API request shapes from naming similarity alone; verify against the provider's OpenAPI/docs first.

### Details
A TorBox integration was drafted by analogy to the earlier Real-Debrid flow without first checking TorBox's API schema. After reviewing TorBox's OpenAPI spec, the endpoint paths were correct, but `controltorrent` expects a JSON body, not form data. The implementation needed correction before the PR could be trusted.

### Suggested Action
For future provider swaps, inspect the live OpenAPI schema or official docs before coding, especially auth style, request content type, and response shape.

### Metadata
- Source: user_feedback
- Related Files: src/clients/torbox.py
- Tags: torbox, api, verification, docs

---
