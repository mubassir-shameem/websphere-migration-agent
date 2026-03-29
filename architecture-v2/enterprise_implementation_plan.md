# Implementation Plan: was2oss-v2 Software Factory

## Goal Description
The objective is to physically build the `was2oss-v2` migration pipeline: an autonomous, multi-agent Graph-RAG architecture that safely migrates legacy WebSphere Application Server (WAS) monoliths to Open Liberty. This plan implements the specifications defined in `enterprise_migration_architecture.md`.

## Proposed Changes

### 1. Foundation & Phase 0 (BYOR Ingestion)
Establish the pipeline structure and the optional IBM report import parsers.
#### [NEW] `was2oss-v2/bin/run_migration.sh`
- Main entry shell script. Initializes the python virtual environment.
#### [NEW] `was2oss-v2/phase0/byor_ingestor.py`
- Python logic to read uploaded JSON/XML reports from IBM Transformation Advisor and WAMT Binary Scanner.
- Normalizes proprietary findings into standardized `IBM_KNOWN_ISSUE` python dictionary representations.

---

### 2. Phase 1 (Semantic Code Graph Builder)
Build the non-AI parsing infrastructure required to protect the system from token limits and hallucinations.
#### [NEW] `was2oss-v2/graph/scg.py` & `schema.py`
- Define the in-memory property graph (NetworkX) and the Dataclass types (`JavaClass`, `Interface`, `JNDI`, `JMSResource`, `AuthAlias`).
#### [NEW] `was2oss-v2/phase1/java_parser.py`
- Use the `javalang` library (or JavaParser subprocess) to walk ASTs. Link `[JavaClass]` nodes to `[Interface]` nodes.
- Classify and inject `GLOBAL` and `COMPONENT` JNDI resolution paths into the SCG.
#### [NEW] `was2oss-v2/phase1/xml_parser.py`
- Use `xml.etree` or `lxml` to parse `ibm-web-bnd.xml` and `ibm-ejb-jar-bnd.xml`.
- Extract `Class-Path` manifests from EAR structures.
#### [NEW] `was2oss-v2/phase1/auth_alias_validator.py`
- Script that runs post-SCG ingestion. Scans all referenced authentication aliases against declared security blocs. If no match is found, flags the node explicitly as `GHOST_ALIAS -> REMOVE`.

---

### 3. Phase 2 (The Orchestrator)
Implement the "Planner" LLM and define the routing logic.
#### [NEW] `was2oss-v2/phase2/orchestrator.py`
- Formulates a system prompt supplying *only* summarized queries from the SCG (e.g., list of components, mapped vs unmapped resources). 
- Generates JSON array of Actionable Tickets ordered by Tiers (`T0`, `T1`, `T2`, `T3` etc.).
#### [NEW] `was2oss-v2/phase2/human_escalator.py`
- Logic to execute `Tier 0-H` hard stops. Automatically scans SCG for Custom CICS `.rar` adapters or Massive JSP frontend payloads. Generates `escalation_report.md` for the user.

---

### 4. Phase 3 (Execution Swarm & Self-Healing QA)
Build the specialized AI sub-agents that operate on narrow context windows.
#### [NEW] `was2oss-v2/phase3/config_synthesizer.py`
- Deterministic Rule Engine with LLM Fallback.
- Reads Tier 2 Config tickets. Applies non-negotiable Liberty rules (e.g., matching paired `jmsQueue` + `jmsQueueConnectionFactory` elements).
#### [NEW] `was2oss-v2/phase3/api_bridger.py`
- The specialized AI. Targets `IBM_KNOWN_ISSUE` tasks involving CommonJ/D-Cache. 
- Employs AST chunking to isolate the failing method, slices the imports out, prompts LLM for Standard JSR replacement, and injects back into the AST frame.
#### [NEW] `was2oss-v2/phase3/code_transformer.py`
- Standard LLM transformer. Receives Tier 4 code tickets. Fixes EJB vs CDI injection conflicts.
#### [NEW] `was2oss-v2/phase3/qa_loop.py`
- The Self-Healing Detective. Boots Liberty via `subprocess.Popen(["mvn", "liberty:run"])`.
- Tails `messages.log` and matches WebSphere Warning/Error codes using predefined JSON regex sets. If `NameNotFoundException` occurs, dispatches micro-ticket back to Config Synthesizer. Fails fast after 10 loops.

## Verification Plan

### Automated Tests
- Scaffold `test_enterprise/` containing a dummy multi-module EAR with mocked proprietary IBM CommonJ and DistributedMap dependencies.
- Verify `byor_ingestor.py` correctly converts raw IBM JSON to SCG nodes.
- Verify that `qa_loop.py` successfully reads a mock `messages.log` containing a `CWWKZ0001I` success message vs a `CNTR4016W MDB unavailable` (which it must mark as WARNING, not FAILURE).

### Manual Verification
- Execute `bin/run_migration.sh` against the legacy DayTrader archive as a baseline, ensuring complete autonomous passability with zero human interventions and perfect JNDI binding resolution.
