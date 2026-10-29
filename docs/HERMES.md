# Hermes team contract

The roster is executable in `gsn.adapters.ROLES` and visible from `GET /agents`. `HermesAdapter.run(role, instruction)` is a transport-independent Python protocol. `MockHermes` records a simulated result. `UnconfiguredHermes` refuses live execution. We have not assumed a particular Hermes CLI, API route or installed version.

| Role | Responsibility | Expected reviewable output |
|---|---|---|
| Orchestrator | Own the production plan and dependencies | Task graph, assumptions, approvals needed |
| Producer | Scope, schedule and budget | Production brief and bounded estimate |
| Scriptwriter | Narrative and advertising script | Script with claims needing evidence |
| Storyboard | Script-to-scene breakdown | Ordered shot list and scene descriptions |
| Character specialist | Authorized appearance references | Character reference manifest |
| Voice specialist | Authorized recordings and direction | Voice manifest and pronunciation notes |
| Cinematographer | Camera and framing | Per-scene camera plan |
| Art director | Sets, wardrobe and lighting | Visual style guide |
| Render planner | Versioned inputs and budget | Model/workflow request proposal |
| Editor | Assembly, timing and export | Edit decision list |
| Audio specialist | Music, effects and levels | Audio plan and license references |
| Quality reviewer | Identity, artifacts and timing | Pass/fail findings with evidence |
| Delivery specialist | Metadata and client handover | Export checklist for human approval |

The orchestrator is one role; the other twelve are specialists. Phase 1 does not autonomously dispatch a task graph: the user selects a role and submits a task. It persists the instruction, project, simulated response and audit event. Role descriptions define responsibilities, not access credentials.

## Connecting the installed Hermes later

1. Record the actual Hermes package/version and its documented invocation interface on Joke’s machine. Do not invent commands based on this adapter name.
2. Implement a new class conforming to `HermesAdapter`. Use an argument list, never shell-interpolate scripts or user instructions. Add timeout, output-size bound, structured response validation and explicit errors.
3. Extend task requests with tenant/project-scoped data references and a unique task ID. Send approved input only; do not grant database admin credentials or unrestricted file access.
4. Have the orchestrator emit a proposed task graph. Human review approves scope and cost. Specialists may propose changes; backend authorization remains authoritative. No agent can grant consent or publish a client deliverable.
5. Test success, invalid output, timeout, cross-tenant reference rejection and replay before enabling live mode. Store live task IDs and version information in audit events. Update `docs/VERIFICATION.md` with actual evidence.

For concurrent coding, assign one owner per directory. API schemas are a shared contract: agree on changes before dashboard and worker work starts. Never let several coding agents independently change the database schema on the same branch.
