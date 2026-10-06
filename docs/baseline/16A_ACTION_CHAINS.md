# 16A — 15 ACTION CHAINS
Each chain is a delivery contract.
## AC-01 — Project Discovery
**ID:** AC-01  
**Name:** Project Discovery  
**Objective:** Freeze product-first context and evidence rules  
**Input:** source report; master prompt  
**Preconditions:** none  
**Tasks/Subtasks:** inventory sources; identify known/unknown; establish status tags  
**Backend impact:** No runtime change  
**Frontend impact:** No UI change  
**Database impact:** N/A  
**Vector DB impact:** N/A  
**Security impact:** Defines isolation needs  
**Files involved:** 00,01,24 docs  
**Dependencies:** none  
**Expected Output:** approved context baseline  
**Validation:** review against source  
**Test cases:** DOC-AC01  
**Acceptance Criteria:** No unsupported requirement  
**Definition of Done:** context versioned  
**Risks:** scope drift  
**Rollback strategy:** revert docs via Git  
**Exit Gate:** Context approved  

## AC-02 — Requirement Normalization
**ID:** AC-02  
**Name:** Requirement Normalization  
**Objective:** Convert source content to traceable requirements  
**Input:** AC-01  
**Preconditions:** context approved  
**Tasks/Subtasks:** normalize FR/NFR/SEC/OPS; assign IDs; map source status  
**Backend impact:** Defines backend obligations  
**Frontend impact:** Defines UI obligations  
**Database impact:** N/A  
**Vector DB impact:** N/A  
**Security impact:** Security requirements explicit  
**Files involved:** 02,17,18  
**Dependencies:** AC-01  
**Expected Output:** requirement baseline  
**Validation:** traceability review  
**Test cases:** DOC-AC02  
**Acceptance Criteria:** All P0 requirements testable  
**Definition of Done:** IDs stable  
**Risks:** requirement ambiguity  
**Rollback strategy:** restore prior baseline  
**Exit Gate:** Requirements approved  

## AC-03 — Scope & MVP Definition
**ID:** AC-03  
**Name:** Scope & MVP Definition  
**Objective:** Prevent raw-PE/extra features from blocking MVP  
**Input:** requirements  
**Preconditions:** AC-02  
**Tasks/Subtasks:** classify MVP/Phase2/Future/Out-of-scope  
**Backend impact:** vector-first  
**Frontend impact:** Streamlit MVP  
**Database impact:** N/A  
**Vector DB impact:** N/A  
**Security impact:** raw file path isolated  
**Files involved:** 03  
**Dependencies:** AC-02  
**Expected Output:** scope baseline  
**Validation:** scope review  
**Test cases:** DOC-AC03  
**Acceptance Criteria:** No P0 feature outside scope  
**Definition of Done:** scope frozen  
**Risks:** scope creep  
**Rollback strategy:** revert change request  
**Exit Gate:** MVP frozen  

## AC-04 — Domain Modeling
**ID:** AC-04  
**Name:** Domain Modeling  
**Objective:** Define analysis/evidence/evaluation invariants  
**Input:** requirements  
**Preconditions:** AC-03  
**Tasks/Subtasks:** aggregates; states; invariants; custody model  
**Backend impact:** typed models  
**Frontend impact:** result model  
**Database impact:** N/A  
**Vector DB impact:** N/A  
**Security impact:** manifest isolation  
**Files involved:** 04  
**Dependencies:** AC-03  
**Expected Output:** domain contracts  
**Validation:** model review  
**Test cases:** UT-domain  
**Acceptance Criteria:** No leakage invariant violated  
**Definition of Done:** contracts versioned  
**Risks:** domain duplication  
**Rollback strategy:** roll back incompatible model  
**Exit Gate:** Domain approved  

## AC-05 — System Architecture
**ID:** AC-05  
**Name:** System Architecture  
**Objective:** Freeze modular dataflow and boundaries  
**Input:** domain + scope  
**Preconditions:** AC-04  
**Tasks/Subtasks:** define runtime/evaluation flows; research vs production adapters  
**Backend impact:** module boundaries  
**Frontend impact:** API-only data access  
**Database impact:** filesystem evidence  
**Vector DB impact:** N/A  
**Security impact:** trust boundaries  
**Files involved:** 05 + ADRs  
**Dependencies:** AC-04  
**Expected Output:** architecture baseline  
**Validation:** failure-mode walkthrough  
**Test cases:** ARCH-01  
**Acceptance Criteria:** Interfaces explicit  
**Definition of Done:** architecture frozen  
**Risks:** adapter coupling  
**Rollback strategy:** ADR rollback  
**Exit Gate:** Architecture approved  

## AC-06 — Repository Structure
**ID:** AC-06  
**Name:** Repository Structure  
**Objective:** Create implementation-ready monorepo  
**Input:** architecture  
**Preconditions:** AC-05  
**Tasks/Subtasks:** directories; ownership; no duplicated logic  
**Backend impact:** backend tree  
**Frontend impact:** frontend tree  
**Database impact:** N/A  
**Vector DB impact:** N/A  
**Security impact:** separate evaluation secrets  
**Files involved:** 06 + skeleton  
**Dependencies:** AC-05  
**Expected Output:** runnable skeleton  
**Validation:** tree + import checks  
**Test cases:** UT-bootstrap  
**Acceptance Criteria:** Tree matches ownership  
**Definition of Done:** bootstrap tests pass  
**Risks:** cross-layer logic  
**Rollback strategy:** git revert  
**Exit Gate:** Skeleton ready  

## AC-07 — Data Architecture
**ID:** AC-07  
**Name:** Data Architecture  
**Objective:** Lock vector schema, views and persistence approach  
**Input:** scope + architecture  
**Preconditions:** AC-06  
**Tasks/Subtasks:** 2381 validation; view map; evidence storage; DB applicability  
**Backend impact:** data module  
**Frontend impact:** input UX  
**Database impact:** No relational DB MVP  
**Vector DB impact:** N/A  
**Security impact:** input sanitization  
**Files involved:** 07,08, configs  
**Dependencies:** AC-06  
**Expected Output:** versioned schema/map  
**Validation:** TC-01/02  
**Test cases:** TC-01,TC-02  
**Acceptance Criteria:** 2381 + locked mapping  
**Definition of Done:** schema tests pass  
**Risks:** wrong mapping  
**Rollback strategy:** config rollback  
**Exit Gate:** Data contract ready  

## AC-08 — Backend Architecture
**ID:** AC-08  
**Name:** Backend Architecture  
**Objective:** Implement orchestrated analysis core  
**Input:** data/model specs  
**Preconditions:** AC-07  
**Tasks/Subtasks:** model adapter; SHAP; M1-M5 protocols; fusion; audit  
**Backend impact:** primary impact  
**Frontend impact:** none  
**Database impact:** artifact writes  
**Vector DB impact:** N/A  
**Security impact:** fail-safe/audit  
**Files involved:** 09 + backend  
**Dependencies:** AC-07  
**Expected Output:** service interfaces  
**Validation:** unit/integration  
**Test cases:** UT/IT-core  
**Acceptance Criteria:** No ground truth dependency  
**Definition of Done:** core tests pass  
**Risks:** scientific config drift  
**Rollback strategy:** strategy rollback  
**Exit Gate:** Core ready  

## AC-09 — API Contract
**ID:** AC-09  
**Name:** API Contract  
**Objective:** Expose explicit transport contract  
**Input:** backend interfaces  
**Preconditions:** AC-08 contracts  
**Tasks/Subtasks:** OpenAPI; endpoints; error codes; versioning  
**Backend impact:** route adapters  
**Frontend impact:** API client  
**Database impact:** N/A  
**Vector DB impact:** N/A  
**Security impact:** CORS/auth boundary  
**Files involved:** 10 + openapi  
**Dependencies:** AC-08  
**Expected Output:** stable REST contract  
**Validation:** API contract tests  
**Test cases:** API-*  
**Acceptance Criteria:** Frontend/backend compatible  
**Definition of Done:** contract tests pass  
**Risks:** breaking change  
**Rollback strategy:** version/revert contract  
**Exit Gate:** API frozen  

## AC-10 — Frontend Architecture
**ID:** AC-10  
**Name:** Frontend Architecture  
**Objective:** Build SOC UI without scientific logic  
**Input:** API contract  
**Preconditions:** AC-09  
**Tasks/Subtasks:** input/status/cards/view/evidence export  
**Backend impact:** none  
**Frontend impact:** primary impact  
**Database impact:** N/A  
**Vector DB impact:** N/A  
**Security impact:** no sensitive path exposure  
**Files involved:** 11 + frontend  
**Dependencies:** AC-09  
**Expected Output:** usable Streamlit UI  
**Validation:** UI smoke/e2e  
**Test cases:** E2E-*  
**Acceptance Criteria:** Exact backend values rendered  
**Definition of Done:** demo badge + errors  
**Risks:** logic duplication  
**Rollback strategy:** UI rollback  
**Exit Gate:** UI integrated  

## AC-11 — Authentication & Security
**ID:** AC-11  
**Name:** Authentication & Security  
**Objective:** Enforce local-safe defaults and blind isolation  
**Input:** architecture/API  
**Preconditions:** AC-05  
**Tasks/Subtasks:** isolation; upload controls; auth gate; secrets; access tests  
**Backend impact:** middleware/policies  
**Frontend impact:** status messaging  
**Database impact:** N/A  
**Vector DB impact:** N/A  
**Security impact:** primary impact  
**Files involved:** 12 + security tests  
**Dependencies:** AC-05,09  
**Expected Output:** security baseline  
**Validation:** negative/access tests  
**Test cases:** SEC-*  
**Acceptance Criteria:** No manifest access  
**Definition of Done:** security tests pass  
**Risks:** public exposure without auth  
**Rollback strategy:** disable exposure  
**Exit Gate:** Security gate  

## AC-12 — AI/RAG Applicability
**ID:** AC-12  
**Name:** AI/RAG Applicability  
**Objective:** Prevent unjustified RAG/vector scope  
**Input:** requirements  
**Preconditions:** AC-02  
**Tasks/Subtasks:** document N/A and guard against dependency creep  
**Backend impact:** none  
**Frontend impact:** none  
**Database impact:** none  
**Vector DB impact:** NOT APPLICABLE  
**Security impact:** avoid unnecessary attack surface  
**Files involved:** 13  
**Dependencies:** AC-02  
**Expected Output:** N/A decision  
**Validation:** dependency review  
**Test cases:** DOC-AC12  
**Acceptance Criteria:** No RAG dependency  
**Definition of Done:** N/A documented  
**Risks:** scope creep  
**Rollback strategy:** remove dependency  
**Exit Gate:** N/A confirmed  

## AC-13 — Testing & Quality Gate
**ID:** AC-13  
**Name:** Testing & Quality Gate  
**Objective:** Implement TC/SE/SC evidence-first verification  
**Input:** all specs  
**Preconditions:** AC-08+  
**Tasks/Subtasks:** unit/integration/api/ui/security/perf/E0-E5/blind  
**Backend impact:** test hooks  
**Frontend impact:** e2e  
**Database impact:** N/A  
**Vector DB impact:** N/A  
**Security impact:** security verification  
**Files involved:** 14,20, tests  
**Dependencies:** AC-08..11  
**Expected Output:** test/evidence suite  
**Validation:** full suite  
**Test cases:** TC-01..20  
**Acceptance Criteria:** No fake PASS  
**Definition of Done:** evidence attached  
**Risks:** missing artifacts  
**Rollback strategy:** retest same config  
**Exit Gate:** Quality gate passed  

## AC-14 — DevOps / Deployment
**ID:** AC-14  
**Name:** DevOps / Deployment  
**Objective:** Build reproducible environments and release tuple  
**Input:** core + tests  
**Preconditions:** AC-13 foundation tests  
**Tasks/Subtasks:** Docker; CI; health; logging; rollback  
**Backend impact:** container  
**Frontend impact:** container  
**Database impact:** N/A  
**Vector DB impact:** N/A  
**Security impact:** non-root/secrets  
**Files involved:** 15 + infra  
**Dependencies:** AC-06,13  
**Expected Output:** deployable candidate  
**Validation:** build/smoke/load  
**Test cases:** SE-02,03,05  
**Acceptance Criteria:** reproducible build  
**Definition of Done:** image/checksum evidence  
**Risks:** env drift  
**Rollback strategy:** rollback release tuple  
**Exit Gate:** Staging ready  

## AC-15 — Final Readiness Gate
**ID:** AC-15  
**Name:** Final Readiness Gate  
**Objective:** Accept product and prepare report evidence  
**Input:** all chains  
**Preconditions:** AC-13/14  
**Tasks/Subtasks:** audit blockers; blind run; release evidence; handover  
**Backend impact:** accepted backend  
**Frontend impact:** accepted UI  
**Database impact:** N/A unless added  
**Vector DB impact:** N/A  
**Security impact:** acceptance review  
**Files involved:** 24 + release docs  
**Dependencies:** AC-01..14  
**Expected Output:** signed evidence package  
**Validation:** reproduction + checklist  
**Test cases:** SE/SC  
**Acceptance Criteria:** Mandatory criteria resolved  
**Definition of Done:** release archived  
**Risks:** premature PASS  
**Rollback strategy:** reject/reopen plan  
**Exit Gate:** Product accepted
