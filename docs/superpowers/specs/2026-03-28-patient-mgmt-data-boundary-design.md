# Patient Management Data Boundary Design
Date: 2026-03-28
Status: Draft for review

## 1. Background

`patient_mgmt` has now completed the first runtime extraction step:

- the module has its own FastAPI entrypoint
- module routes no longer import platform auth dependencies
- the platform no longer mounts `patient_mgmt` in-process
- the platform passes signed module context instead of sharing runtime helpers

That establishes the runtime boundary, but not the data boundary.

Patient data is still effectively owned by the platform backend codebase and migration flow. As long as that remains true, `patient_mgmt` is still only partially extracted. The next step must move patient data ownership into the module service without breaking current read and write flows.

## 2. Problem Statement

The current system still has three structural problems.

### 2.1 Data Ownership Is Not Yet Real

`patient_mgmt` does not yet own a database boundary that it can migrate, back up, and operate independently.

### 2.2 Platform and Module Boundaries Would Re-Couple During Growth

If the platform continues to read patient tables directly, then even after service extraction the platform remains coupled to patient storage layout, migration timing, and rollback constraints.

### 2.3 Cutover Risk Is High Without a Transitional Model

A one-shot migration from platform-owned patient data to module-owned patient data would create avoidable risk. Historical backfill, new writes, and read consistency need an explicit migration pattern.

## 3. Goals

This phase must achieve the following:

- give `patient_mgmt` ownership of its own persistence boundary
- keep the platform as the control plane for identity, entitlements, and module discovery
- stop the platform from directly querying patient business tables
- define a stable synchronous API contract from platform to `patient_mgmt`
- preserve patient lifecycle events as module-owned contracts
- support a controlled migration with backfill, temporary dual-write, and final read/write cutover

## 4. Non-Goals

This phase does not require:

- extracting `assessment`
- redesigning the frontend shell
- replacing the platform control plane
- removing every compatibility shim immediately
- introducing a multi-service reporting architecture for every admin page
- fully independent infrastructure for `patient_mgmt` outside the current Postgres environment

## 5. Deployment Decision

The recommended deployment model for this phase is:

- same Postgres instance
- separate database for `patient_mgmt`

This is preferred over a separate schema because a separate database creates a harder ownership boundary:

- migrations are harder to accidentally couple
- direct cross-module reads become less convenient and therefore less likely
- rollback and backup boundaries are clearer

If operations constraints make a separate database impossible in the short term, a schema split may be used only as a temporary fallback. It should not be treated as the target end state.

## 6. Target Ownership Model

### 6.1 Platform Database Ownership

The platform database continues to own control-plane data only:

- tenants
- plans
- subscriptions
- entitlements
- module catalog
- module deployment metadata
- platform user and permission data

The platform database must not remain the source of truth for patient business records.

### 6.2 Patient Module Database Ownership

The `patient_mgmt` database must own:

- patient master records
- patient search and listing fields
- patient module business state
- patient module outbox or event persistence records
- module-local schema migrations

The module database becomes the primary persistence boundary for patient business behavior.

## 7. Service Boundary

The runtime boundary from Step 1 stays in place and is extended with a data boundary:

- the platform authenticates the caller
- the platform resolves entitlement and module availability
- the platform forwards requests or the frontend calls the module through a platform-governed route
- the platform provides signed module context
- `patient_mgmt` validates the signed context and serves the patient business request

The module service must not query platform control-plane tables directly.

The platform must not query patient business tables directly.

## 8. Integration Model

The integration model for this phase has two paths.

### 8.1 Online Request Path

Online business requests between platform and `patient_mgmt` should use synchronous HTTP.

This path must cover at minimum:

- patient list
- patient detail
- patient create
- patient update
- patient delete

The purpose of this phase is to establish a clean request boundary, not to optimize every cross-service call.

### 8.2 Event Path

Patient lifecycle changes remain module-owned events.

At minimum, the module must continue to publish:

- patient created
- patient updated
- patient deleted

The event bus remains the right boundary for downstream consumers, projections, and later cross-module read models.

## 9. Migration Strategy

The migration should happen in five stages.

### Stage A: Establish the Module Database

Create a dedicated database connection and migration chain for `patient_mgmt`.

Deliverables:

- module-specific database settings
- module-specific engine and session handling
- module-specific migration path
- initial patient schema in the module database

At the end of this stage, `patient_mgmt` must be able to start against its own database even if the platform still owns current traffic.

### Stage B: Historical Backfill

Backfill existing patient records from the current source into the module database.

Requirements:

- backfill must be idempotent
- repeated runs must not create duplicates
- tenant ownership must be preserved exactly
- record identifiers must remain stable

This stage creates data parity without changing live read/write ownership yet.

### Stage C: Dual-Write Transition

New patient write operations should be handled by the module service and mirrored or validated against the old source during a temporary compatibility period.

During this stage:

- the module database is treated as the forward-moving target
- the old source exists only for compatibility and parity checks
- drift detection should be explicit, not assumed

This stage should be time-boxed. Long-lived dual-write is not acceptable as a resting architecture.

### Stage D: Read Cutover

Once parity is validated, platform-driven patient reads must switch to `patient_mgmt` APIs.

This includes:

- patient list
- patient detail
- patient search

At the end of this stage, the platform no longer directly depends on patient storage layout.

### Stage E: Write Cutover and Freeze

Once reads are stable, the old patient source must be frozen and removed from the write path.

After this:

- `patient_mgmt` is the sole write owner
- old patient tables become read-only or are scheduled for retirement
- rollback, if needed, is an explicit operational procedure rather than normal application behavior

## 10. Migration Scope

This phase should move only the data necessary to establish a real patient service boundary.

### 10.1 In Scope

- patient master table data
- patient list/detail/search fields
- patient module outbox or event records
- module-local persistence abstractions needed to isolate the database boundary

### 10.2 Out of Scope

- unrelated module data
- cross-module analytics projections
- broad admin-reporting redesign
- generalized service mesh or distributed transaction tooling

## 11. Contract Requirements

This phase needs three explicit contracts.

### 11.1 Platform to Module Request Contract

The synchronous API contract must support:

- list patients
- get patient detail
- create patient
- update patient
- delete patient

These requests must carry the signed module context introduced in Step 1.

### 11.2 Signed Module Context Contract

The signed context remains the only accepted authority for:

- tenant identity
- user identity
- user scope
- permission set
- authorized module proof
- request correlation metadata if present

The module must not fall back to raw untrusted request headers for authorization semantics.

### 11.3 Module Event Contract

The event contract for patient lifecycle changes must remain explicit and versionable.

At minimum, each event must continue to include:

- patient identifier
- tenant identifier
- source module identifier
- event type

## 12. Testing Strategy

This phase must be validated at four levels.

### 12.1 Module Migration Tests

Prove that the module database can initialize and migrate independently.

### 12.2 Backfill Tests

Prove that historical import is idempotent and preserves tenant ownership.

### 12.3 Dual-Write Consistency Tests

Prove that a patient write in the transition period keeps old and new sources aligned or surfaces drift explicitly.

### 12.4 Read-Cutover Regression Tests

Prove that patient list, detail, and search continue to behave correctly once reads come from `patient_mgmt`.

## 13. Success Criteria

This phase is complete only when all of the following are true:

- `patient_mgmt` can start while connected only to its own database
- platform code no longer directly accesses patient business tables
- patient CRUD flows execute through the module service boundary
- historical patient backfill can be run repeatedly without duplicate corruption
- read cutover is in place for patient list, detail, and search
- module events still emit with stable payloads
- backend test coverage includes migration, backfill, and cutover behavior

## 14. Risks

The main risks are:

- dual-write drift if the transition period is allowed to linger
- accidental cross-database reads reintroducing hidden coupling
- cutover gaps where some patient views still query the old source
- unclear rollback expectations after partial migration

These risks are manageable only if the migration phases are explicit and time-bounded.

## 15. Decision

Phase 2 Step 2 should move `patient_mgmt` to a dedicated database on the existing Postgres instance, define HTTP as the primary online integration path, keep events as the asynchronous integration path, and migrate data through backfill followed by a temporary dual-write window and final read/write cutover.
