# End-to-End Enterprise WAS-to-Open-Liberty Architecture

## 1. The Catalyst & The Thought Process
The necessity for this redesigned architecture stems directly from our experiences migrating IBM DayTrader from WebSphere Application Server (tWAS) to Open Liberty using a generalized, single-agent LLM assistant. 

While the agent excelled at raw syntactical translation (e.g., swapping `javax.ejb.Stateless` for `@Inject`), it fundamentally failed at **topological awareness**. We observed four critical failure categories that proved a single conversational agent cannot migrate an enterprise monolith:

1. **Token Overflow on Complex Classes:** Massive utility or controller classes (like `TradeDirect.java`) exceeded the safe context window of the LLM. The agent would unpredictably truncate its own response, losing critical business logic.
2. **JNDI Context Disconnects:** Java code (`@Resource(name="jms/Queue")`), deployment bindings (`ibm-ejb-jar-bnd.xml`), and the physical server configuration (`server.xml`) live in different files. Because the single-agent could not cross-reference them reliably in memory, it routinely generated mismatched endpoints causing `NameNotFoundException`s.
3. **Ghost Security Aliases:** The agent blindly translated every `authentication-alias` found in legacy binding files. Because it didn't verify if those aliases actually existed in the target security stanza, it generated fictitious LDAP/DB auth elements, which explicitly crashed the Open Liberty Derby connection pool.
4. **Classloader Isolation Conflicts:** A traditional WAS server handles WAR-packaged EJBs differently than Open Liberty's CDI-first container context. The AI repeatedly failed to realize that deploying an EJB within a WAR requires a `<classLoader delegation="parentLast"/>` directive in `server.xml`.

The conclusion: Converting a monolith requires a **Multi-Agent, Graph-RAG (Retrieval-Augmented Generation) Architecture**.

## 2. The Enterprise Shift
While DayTrader proved the need for Graph-RAG, DayTrader is ultimately a standard Java EE application. True enterprise WebSphere applications introduce a vastly more complex layer of proprietary vendor lock-in. 

Therefore, this architecture is explicitly designed to handle, or safely escalate, the following "dark corners" of Enterprise WAS:
- **Proprietary IBM APIs:** Asynchronous Beans/CommonJ (`WorkManager`) and Dynamic Caching (`DistributedMap`).
- **Complex Topologies:** Java 2 Connectors (JCA) for Mainframes/CICS and Multiple Security Domains (Custom Trust Association Interceptors).
- **Multi-Module Boundaries:** Massive `.ear` applications relying heavily on Shared Library `Class-Path` manifests across dozens of EJB `.jar`s.

---

## 3. The 4-Phase Software Factory Architecture

### Phase 0: Optional BYOR (Bring Your Own Report) Drop Zone
Enterprise security policies dictate that third-party AI agents cannot connect to live production WebSphere cells. Therefore, the pipeline begins with an optional "Bring Your Own Report" drop zone. 

Users can upload pre-generated reports from:
- **IBM Transformation Advisor (TA)** (JSON Exports)
- **WebSphere Application Migration Toolkit (WAMT)** (XML/HTML Reports)

**Why this is crucial:** If these reports are provided, the agent parses them and injects the findings directly into the machine's memory graph. The AI is saved from blindly hallucinating fixes for deeply proprietary IBM dependencies because the IBM reports explicitly flag them *before* any transformer agent touches the code.

---

### Phase 1: Ingestion & The Semantic Code Graph (SCG)
To solve the "Context Disconnect" and "Token Overflow" problems, the system uses deterministic parsers (JavaParser, dom4j) to build a **Semantic Code Graph (SCG)** before the AI is invoked.

The Graph builds explicit, non-hallucinated relationships. For example:
```text
[JavaClass: TradeSLSBBean]
  --IMPLEMENTS--> [Interface: TradeSLSBLocal]
  --HAS_RESOURCE {name:"jms/TopicConnectionFactory", path:COMPONENT}--> [JMSResource: jms/TopicConnectionFactory]
  
[BindingFile: ibm-ejb-jar-bnd.xml]
  --MAPS_RESOURCE {from:"jms/TopicConnectionFactory"}--> [GlobalJNDI: "jms/TradeStreamerTCF"]
  
[ReportNode: IBM_KNOWN_ISSUE]
  --FLAGS_API {api:"com.ibm.websphere.cache.DistributedMap"}--> [JavaMethod: CacheManager.init()]
```
The SCG also explicitly parses EAR `MANIFEST.MF` boundaries, mapping `Class-Path` dependencies to ensure cross-module classloader injection in `server.xml`.

---

### Phase 2: Orchestration & The Tiered Ticket System
An **Orchestrator LLM** reads summarized metrics of the Semantic Code Graph (never the raw files). Its sole job is to generate a strict, ordered list of execution tickets. 

Because we are dealing with enterprise payloads, the Orchestrator forces a strict dependency hierarchy:

*   **Tier 0-H (Human Escalations & Hard Stops):**
    *   If the SCG detects Custom CICS `.rar` adapters, Multiple Security Domains, or massive unsupported JSF/JSP UI bundles, the Orchestrator halts auto-generation for that module. It generates a Markdown escalation report instructing the human architect exactly where manual Day 2 intervention is required.
*   **Tier 0 (Pre-flight):** Disk space checks, staging specific JDBC drivers.
*   **Tier 1 (Dependencies):** Generating standard Jakarta EE `pom.xml` dependencies.
*   **Tier 2 (Config Translation):** Generating `server.xml`. Filtering out `GHOST_ALIAS` security paths. Mapping JNDI resources based purely on SCG edges.
*   **Tier 3 (Bulk Deterministic):** Running standard OpenRewrite recipes (e.g., `javax` to `jakarta`).
*   **Tier 4 (Targeted AI Transform):** Fixing specific CDI injection ambiguities.
*   **Tier 5 (API Bridging):** Stripping proprietary `com.ibm.websphere.*` logic and rewriting to modern standards.

---

### Phase 3: Distributed Multi-Agent Execution

If a ticket passes the Orchestrator, it is routed to a specialized AI worker with a narrow instruction set:

1. **The Config Synthesizer (Rule Engine + AI Fallback):** 
   - Generates the Open Liberty `server.xml`. 
   - Applies strict non-negotiable rules: Every mapped JMS Queue must have a paired Connection Factory. Every EJB deployment must receive a `parentLast` classloader delegation. Fake security aliases flagged by the SCG are hard-deleted.
2. **The API Bridger (Specialized AI):**
   - Targets the `IBM_KNOWN_ISSUE` proprietary APIs flagged in Phase 1.
   - Uses **Abstract Syntax Tree (AST) Contextual Chunking** to slice out the IBM import (e.g., CommonJ `WorkManager`), feeds only that single method to the LLM, and rewrites the task to standard `javax.enterprise.concurrent` logic. This prevents the 1000-line token truncation we saw in DayTrader.
3. **The Code Transformer (AI):**
   - Modifies Java source files to resolve CDI (`@Inject`) vs EJB (`@EJB`) mismatches.
   - Every LLM output is structurally validated against the original interface method signatures defined in the SCG.
4. **The QA/Self-Healing Loop (Detective):**
   - Compiles the Maven output and boots Open Liberty in a subprocess.
   - Streams the `messages.log` and uses a mapping rulebook (`error_codes.json`) to classify errors.
   - Example behavior: If it hits `NameNotFoundException`, it acts as a detective. It queries the Graph DB to find the source of the missing JNDI, determines if it's a `GLOBAL` or `COMPONENT` mapping failure, and routes a micro-ticket back to the Config Synthesizer to patch the `server.xml`.
   - Loops a maximum of 10 times before explicitly escalating to human intervention.

---

## 4. What This Leaves for Humans
Even with a flawless Graph-RAG pipeline, these remain strictly Day 2 operational expectations for human engineers:
- **Database Targets:** Swapping the agent's embedded Derby defaults for external DB2/PostgreSQL clusters.
- **Security Architecture:** Reconciling the agent's baseline `ALL_AUTHENTICATED_USERS` mappings with actual LDAP/OIDC corporate registries.
- **Frontend Validation:** The agent strictly focuses on Backend Java and XML. Human engineers must verify JSP/Servlet UI payload execution on the new Liberty runtime.
