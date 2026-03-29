# Spec-Driven Development & Testing Guide: was2oss-v2

Welcome to the **Specification-Driven Development (SDD)** manual for the `was2oss-v2` architecture.

Building an autonomous Migration Factory requires strict bounded contexts. If you attempt to build and test the entire system end-to-end immediately, it will be impossible to debug. Instead, each Phase must be built and tested in isolation using mock inputs and deterministic outputs.

This document details the exact specifications (Input → Expected Output) for each major node in the pipeline, and exactly how to write unit/integration tests for them.

---

## 1. Phase 0: BYOR Ingestor (`byor_ingestor.py`)

**Goal:** Safely parse user-uploaded JSON/XML reports from IBM TA and WAMT Binary Scanner into a structured memory format without executing any binaries.

### Specification
*   **Input:** A mock `recommendations.json` (from IBM TA) containing a list of flagged APIs (e.g., `com.ibm.websphere.cache.DistributedMap`) and their corresponding line numbers in a `.java` file.
*   **Expected Process:** Parse the JSON/XML accurately.
*   **Output Data Structure:** A list of Python dictionaries formatted as:
    ```json
    { "type": "IBM_KNOWN_ISSUE", "file": "CacheManager.java", "line": 42, "api": "DistributedMap", "severity": "HIGH", "strategy": "JCACHE_REWRITE" }
    ```

### How to Test This Phase (Without WebSphere)
1.  **Test 0.1 (JSON Integrity):** Feed the ingestor a handwritten 10-line JSON file mimicking a TA output. Assert that the returned Python list has exactly 1 item and the `strategy` string is correctly populated.
2.  **Test 0.2 (Missing File Gracefulness):** Pass a non-existent path to the ingestor. Assert that it catches the `FileNotFoundError`, logs an `INFO` message ("No BYOR report provided"), and returns an empty `[]` list rather than crashing the pipeline.

---

## 2. Phase 1: Semantic Code Graph Builder (`graph_builder.py`)

**Goal:** Deterministically map the topological relationships of a legacy Java EE application using ASTs and XML parsers.

### Specification
*   **Input Directory:** A mocked directory containing exactly two files:
    *   `TradeSLSBBean.java` (Containing `@Resource(name="jms/Queue") ConnectionFactory qcf;`)
    *   `ibm-ejb-jar-bnd.xml` (Containing `<resource-ref name="jms/Queue" binding-name="jms/RealQueue"/>`)
*   **Expected Process:** `java_parser.py` extracts the `@Resource` AST node. `xml_parser.py` extracts the XML binding node. `graph_builder.py` fuses them in memory using `NetworkX` (or similar).
*   **Output Data Structure:** A Graph object where querying the shortest path between `TradeSLSBBean` and the string `"jms/RealQueue"` returns precisely `1 edge`.

### How to Test This Phase (Without WebSphere)
1.  **Test 1.1 (Graph Pathing):** Write a unit test that builds the graph from the mocked XML/Java. Run a query: `graph.get_downstream_dependencies("TradeSLSBBean")`. Assert that the returned list contains the exact string `"jms/RealQueue"`.
2.  **Test 1.2 (Ghost Alias Detection):** Feed the XML parser an `ibm-web-bnd.xml` containing `<authentication-alias name="FakeAlias"/>` but no corresponding `security-role` or `RunAs` map. Run `auth_alias_validator.py`. Assert that the graph node is marked with `GHOST_ALIAS=True`.

---

## 3. Phase 2: Orchestrator (`orchestrator.py`)

**Goal:** Sequence the migration tickets based strictly on dependency tiers without looking at raw code files.

### Specification
*   **Input Data:** A mocked summarized dictionary of the SCG. Example: `{"total_files": 12, "global_jndi_lookups": 4, "ibm_known_issues": 1}`.
*   **Expected Process:** The Orchestrator LLM applies its strictly typed prompt to the summary.
*   **Output Data Structure:** A JSON array of `Ticket` dataclasses ordered by Tier execution rules.

### How to Test This Phase (Without WebSphere)
1.  **Test 2.1 (Tier Sorting Enforcement):** Provide a mock SCG summary to the Orchestrator. Assert that the resulting JSON array outputs `Tier 0` tickets (like "Generate pom.xml") *before* any `Tier 4` Code Transformation tickets. The array index must be strictly validated `<`.
2.  **Test 2.2 (Human Escalation Hard Stop):** Provide a mock SCG summary containing `{"custom_jca_adapters": 1}`. Assert that the Orchestrator returns a `Tier 0-H` ticket, flags a `HALT_EXECUTION=True` boolean, and successfully writes a local `escalation_report.md` file.

---

## 4. Phase 3: Execution Agents (`config_synthesizer.py` & `api_bridger.py`)

**Goal:** Modify the codebase precisely using narrow-context AI and deterministic rewriting.

### Specification
*   **Input Data:** A `Tier 2` Config Ticket instructing the system to generate a `server.xml` for a JMS Queue, alongside the SCG mapping `{ "jndiName": "jms/RealQueue" }`.
*   **Expected Process:** The Rule Engine translates the mapping into Liberty XML syntax.
*   **Output Data Structure:** An absolute file written to disk (`server.xml`).

### How to Test This Phase (Without WebSphere)
1.  **Test 3.1 (Config Validation):** Feed a mock JMS ticket to the Config Synthesizer. Read the generated `server.xml`. Use standard Python XPath to assert that `//jmsQueueConnectionFactory` exists AND that a paired `//jmsQueue` exists perfectly matching the JNDI name.
2.  **Test 3.2 (API Bridger AST Safety):** Feed the API Bridger a mock `CacheManager.java` containing `import com.ibm.websphere.cache.DistributedMap;` and 50 lines of unrelated business logic. Assert that the returned `.java` file successfully replaced the import with `javax.cache.CacheManager` **but fundamentally preserved the exact character count or MD5 checksum** of the surrounding 50 lines of business logic.

---

## 5. Phase 4: Self-Healing QA Loop (`qa_loop.py`)

**Goal:** Compile the output, map Open Liberty error sequences to fixes, and prevent infinite loops.

### Specification
*   **Input Data:** A mock raw text file mimicking a Liberty `messages.log`.
*   **Expected Process:** Regex parse the IBM `messageId` (e.g., `CNTR4016W`, `CWWKZ0002E`).
*   **Output Data Structure:** A Python Enum classification: `BLOCKING`, `WARNING`, or `FATAL`.

### How to Test This Phase (Without booting the Server)
1.  **Test 4.1 (Warning Bypass):** Feed the QA loop a mock log containing exactly `[WARNING ] CNTR4016W: The message-driven bean destination is not available`. Assert that the `error_classifier.py` maps this to `Enum.WARNING`, logs it, and continues the loop without raising a fix ticket.
2.  **Test 4.2 (Infinite Loop Protection):** Feed the QA loop a mock log containing `[ERROR ] CWWKZ0002E` and rig the `ConfigSynthesizer` mock to fail permanently. Assert that the `qa_loop.py` exits exactly at `iter == 10`, raises a `FatalQAException`, and gracefully shuts down the Liberty `subprocess`.
