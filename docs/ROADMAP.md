# Project Roadmap

This document tracks planned features and ongoing development for the WAS2OSS Agent.

## 🚀 Active Development
- [x] **Core Migration Pipeline** (Upload -> Transform -> Validate -> Download)
- [x] **Cost Optimization**: Default to 1-Pass iteration.
- [x] **Smart Package Detection**: Stop hardcoding `com/company` paths.

## 📅 Planned Features

### Phase 5: Enterprise Integration
- [ ] **IBM AMA Integration**: Parse `analysis.json` from Transformation Advisor to guide the LLM (See `AMA_INTEGRATION.md`).
- [ ] **Custom Rules Engine**: Allow users to define "If you see X, replace with Y" rules (RAG/Knowledge Base).

### Phase 6: Advanced Repairs
- [ ] **Smart Repair**: Instead of re-processing *all* files in Iteration 2, parse `maven` logs and ONLY re-process files that failed compilation.
- [ ] **Diff View**: Show "Before vs After" diffs in the Dashboard before downloading.

### Phase 7: Model Optimization
- [ ] **Haiku Support**: Use Claude Haiku for simple POJO files (10x cheaper) and Sonnet only for complex Servlets/EJBs.
