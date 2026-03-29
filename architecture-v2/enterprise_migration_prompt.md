# Implementation Prompt for Antigravity / Claude Code

> You are building an autonomous WebSphere Application Server (WAS) to Open Liberty migration pipeline. The system is called `was2oss-v2`.

## Project Structure

Create the following directory layout:

```text
was2oss-v2/
  bin/
    run_migration.sh          # entry point
  phase0/
    byor_ingestor.py          # parses user-provided TA + WAMT JSON/XML reports (BYOR Drop Zone)
  phase1/
    java_parser.py            # JavaParser-based AST walker (via subprocess)
    xml_parser.py             # dom4j/JAXB XML + EAR Class-Path parser (via subprocess)
    graph_builder.py          # builds SCG from parse outputs
    jndi_classifier.py        # classifies GLOBAL vs COMPONENT JNDI paths
    auth_alias_validator.py   # detects and flags ghost auth aliases
  phase2/
    orchestrator.py           # reads SCG, generates ordered ticket list & routes Human Escalations
    ticket_schema.py          # dataclass definitions for each ticket type
    dependency_resolver.py    # maps javax imports to Maven Central artifacts
  phase3/
    config_synthesizer.py     # generates server.xml, pom.xml, binding XMLs
    code_transformer.py       # AST chunking + LLM-powered code fixes (CDI/EJB)
    api_bridger.py            # strips proprietary com.ibm.* APIs and rewrites logic (CommonJ, D-Cache)
    openrewrite_runner.py     # runs OpenRewrite Maven plugin recipes
    qa_loop.py                # boots Liberty, reads logs, classifies errors
    error_classifier.py       # maps Liberty messageId → fix strategy
    smoke_tests.py            # curl-based functional verification
  knowledge/
    error_codes.json          # Liberty messageId → classification (blocking/warning/fatal)
    jms_rules.json            # rules: every JMSxCF requires matching JMSx element
    ejb_cdi_rules.json        # rules: @Stateless + @ApplicationScoped is illegal
    classloader_rules.json    # rules: WAR+EJB → parentLast always
    openrewrite_recipes.yaml  # standard javax→jakarta + EJB 3.2 recipes
  graph/
    scg.py                    # Semantic Code Graph API (query and mutate)
    schema.py                 # node types: JavaClass, Interface, JNDI, AuthAlias, IBM_KNOWN_ISSUE
  tests/
    test_enterprise/          # integration test repository payload
```

## Core Requirements

### Phase 0 — BYOR (Bring Your Own Report) Drop Zone
- Expose an upload drop-zone for IBM Transformation Advisor (TA) output (JSON) and WAMT Binary Scanner output (XML/HTML).
- Parse all flagged issues into Semantic Code Graph (SCG) nodes with `type=IBM_KNOWN_ISSUE`.
- If TA/WAMT are not uploaded, log a standard INFO line and proceed autonomously via pure static analysis. The tool must function successfully without these drops.

### Phase 1 — Graph Building & Ingestion
- Parse Java source to extract: class types, annotations, injection points, interface relationships, and JNDI lookups.
- Classify every JNDI lookup as `GLOBAL` (raw `InitialContext.lookup`) or `COMPONENT` (`@Resource` annotation).
- Parse `ibm-web-bnd.xml` and `ibm-ejb-jar-bnd.xml`: extract resource-ref mappings and authentication-alias references.
- For every authentication-alias found in binding files: mark as `UNRESOLVED` until a matching authData id is found via user input or reports. If unresolved: mark as `GHOST_ALIAS` with `fix_strategy=REMOVE_REFERENCE`.
- Parse EAR `MANIFEST.MF` boundaries to map cross-module Shared Libraries (`Class-Path`) to ensure precise dependency graphs.

### Phase 2 — Orchestration & Escalation
- Orchestrator reads SCG via query API (never reads raw files blindly).
- Generates tickets ordered by dependency (Tier 0-H > Tier 0 > Tier 1... etc.).
- **Human Escalation (Tier 0-H):** If SCG detects Custom CICS `.rar` adapters, Multiple Security Domains, or massive JSF/JSP frontend bundles, the Orchestrator halts auto-generation for that specific module and dumps a Markdown escalation report for the user.

### Phase 3 — Execution
**Config Synthesizer**
- `server.xml` generation rules (non-negotiable):
  1. Every JMS `@Resource` with `COMPONENT` path must have its binding resolved to a `jndiName`.
  2. Every `jmsQueueConnectionFactory` must have a paired `jmsQueue` element.
  3. Every `jmsTopicConnectionFactory` must have a paired `jmsTopic` element.
  4. If SCG has any `[JavaClass type=EJB]`: add `<classLoader delegation="parentLast"/>` to webApplication.
  5. Remove ALL authData elements that correspond to `GHOST_ALIAS` nodes.
  6. Set liberty-maven-plugin `<startTimeout>120</startTimeout>`.

**API Bridger (New)**
- Search SCG for `IBM_KNOWN_ISSUE` indicating proprietary APIs (CommonJ `WorkManager`, `DistributedMap` D-Cache).
- Use AST contextual chunking to strip the proprietary `com.ibm.websphere.*` imports and rewrite the task to standard `javax.enterprise.concurrent` or JSR-107 logic.

**Code Transformer**
- For files > 500 lines: use AST chunking (split at method boundaries). Send each chunk with method signature, interface contract, and imports. Reassemble using original AST frame.
- For files ≤ 500 lines: send full file with targeted LLM prompt.
- Every LLM output must be validated: interface method signatures must still exactly match the interface structure in the SCG.

**QA Loop**
- Boot liberty using subprocess: `mvn liberty:run`
- Parse each line of `messages.log` for its messageId prefix.
- Use `error_codes.json` to classify:
  - `BLOCKING` = stop, raise fix ticket, re-run
  - `WARNING` = log, continue (e.g., treat `CNTR4016W MDB unavailable` as a warning, not failure)
  - `FATAL` = escalate to human with full context dump
- Loop max 10 times before explicitly escalating to human intervention.

## LLM Usage Policy
- **Orchestrator:** Summarized SCG context only (< 2000 tokens per call).
- **Config Synthesizer:** Rule-engine first, LLM only for unmapped/fuzzy string cases.
- **Code Transformer / API Bridger:** AST chunk context only (< 3000 tokens per call).
- **QA Classification:** JSON lookup first, LLM only for unknown `messageId`s.

Use Python 3.11+. Use `subprocess` for Java tooling. Use `httpx` for REST callbacks. No Spring, no heavy Python framework bloat. Keep it simple, auditable, and modular.
