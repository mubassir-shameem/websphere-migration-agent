# Validation Fix: javax.* vs jakarta.* Namespace

## Problem

WebSphere applications use `javax.*` imports (Java EE / Jakarta EE 8), but the original pom.xml template used Jakarta EE 9.1 which requires `jakarta.*` imports.

**Example of namespace mismatch:**
```java
// Code uses this (javax.*)
import javax.servlet.http.HttpServlet;

// But pom.xml had this (jakarta.*)
<artifactId>jakarta.servlet-api</artifactId>  // ❌ Won't compile
```

## Solution

Downgraded pom.xml template to **Java EE 8** which uses `javax.*`:

| Dependency | Version | Namespace |
|------------|---------|-----------|
| javaee-web-api | 8.0.1 | javax.* |
| javax.servlet-api | 4.0.1 | javax.* |

## File Changed

`backend/app/agents/transformation.py` - `generate_pom()` method

## Limitation

This is a deterministic template. For robustness at scale:
- Post-process LLM output to detect import patterns
- Dynamically select matching pom.xml version
- Add validation retry with auto-fix
