# Patient Management Read Cutover Design
Date: 2026-03-28
Status: Draft for review

## 1. Background

`patient_mgmt` now has the main Phase 2 Step 2 building blocks:

- module-local database session handling
- module-owned `PatientRecord` persistence
- module-local migration chain
- signed `x-platform-context` token issuance
- a platform-side `PatientModuleProxy`
- backfill and temporary dual-write support

What is still missing is a real platform read cutover. The platform patient API path does not yet decide between a local compatibility path and the extracted `patient_mgmt` service. `PATIENT_MGMT_READ_FROM_SERVICE` exists in configuration, but it is not yet the real switch for patient reads.

## 2. Problem Statement

The current state still has three issues.

### 2.1 Platform Reads Are Not Controlled

The platform does not yet have a single place that decides whether patient reads should come from the extracted module service or a compatibility path.

### 2.2 API Boundaries Are Still Too Implicit

`backend/app/api/v1/patients.py` is still just a compatibility import of the module router. That keeps the platform and module read behavior coupled, even though Phase 2 is supposed to move the platform toward service-to-service integration.

### 2.3 Cutover Risk Is Higher Than It Needs To Be

If read cutover is done by directly rewriting controllers or deleting the compatibility path too early, it becomes harder to isolate regressions in contract mapping, authorization context, and error handling.

## 3. Goals

This phase must:

- make `PATIENT_MGMT_READ_FROM_SERVICE` the real control point for patient read routing
- move platform patient list and detail reads behind a dedicated platform-side read adapter
- use the existing `PatientModuleProxy` for service reads
- preserve current platform response shapes for patient list and detail
- keep write flows unchanged during this step
- keep a compatibility read path available while the flag is off

## 4. Non-Goals

This phase does not include:

- patient create, update, or delete cutover
- expanding dual-write beyond current repository-level support
- deleting the local compatibility read path
- removing backfill support
- changing frontend behavior
- extracting `assessment`

## 5. Recommended Approach

Three implementation directions were considered:

- route-level branching inside the patient API
- a platform-side patient read adapter that owns the switch
- immediate direct cutover to proxy-only reads

The recommended approach is a platform-side read adapter.

This keeps the switch, context construction, contract mapping, and error handling in one place. It also avoids pushing flag logic into route handlers and keeps the next write-cutover phase from inheriting duplicated routing decisions.

## 6. Target Architecture

### 6.1 Platform Patient Read Adapter

Add a dedicated platform service, for example:

- `backend/app/services/patient_read_service.py`

This service becomes the single entry point for:

- patient list
- patient detail

Its responsibilities are:

- build `PatientModuleContext` from the current platform request context
- choose the read path based on `PATIENT_MGMT_READ_FROM_SERVICE`
- call `PatientModuleProxy` when service reads are enabled
- call a local compatibility reader when service reads are disabled
- normalize the result back into the platform API response shape

Routes must not decide between proxy and compatibility logic directly.

### 6.2 Service Read Path

When `PATIENT_MGMT_READ_FROM_SERVICE=true`:

- the platform read adapter uses `PatientModuleProxy`
- the proxy sends signed `x-platform-context`
- `patient_mgmt` validates the token and serves the request
- the platform maps the module contract back to the platform response schema

This becomes the target read path for list and detail.

### 6.3 Compatibility Read Path

When `PATIENT_MGMT_READ_FROM_SERVICE=false`:

- the platform read adapter uses a local compatibility path
- the local path preserves current list/detail behavior
- the route still returns the same response structure as the service path

The compatibility path exists only to reduce cutover risk. It is not the target end state.

## 7. Scope of Cutover

This step cuts over:

- patient list
- patient detail

It intentionally does not cut over:

- patient create
- patient update
- patient delete

List and detail must move together. Splitting them would create inconsistent read semantics, duplicate token/context logic, and harder-to-diagnose differences between what appears in lists and what resolves in detail views.

## 8. Authorization and Context Model

The read adapter must build one consistent `PatientModuleContext` containing:

- `user_id`
- `tenant_id`
- `scope`
- `correlation_id`
- `permissions`
- `entitled_modules`

The platform remains responsible for:

- authenticating the caller
- resolving the caller's permissions
- determining the effective tenant context
- signing the module context token

The module remains responsible for:

- validating the signed token
- enforcing module access and permission checks for module-owned read operations

Routes and controllers should not hand-assemble module tokens. Token construction belongs in the read adapter and proxy path.

## 9. Error Handling

Error behavior must stay explicit.

### 9.1 Authorization Errors

- `401` and `403` from the module path must remain authorization errors
- the platform should not silently downgrade or swallow them

### 9.2 Not Found

- detail reads should keep returning `404` when the patient is not found
- list reads should continue to return an empty collection, not a platform error

### 9.3 Service Failures

When `PATIENT_MGMT_READ_FROM_SERVICE=true`, service failures must be surfaced as failures.

The platform must not silently fall back to the compatibility path on proxy/network/5xx errors. Silent fallback would hide cutover defects and make the rollout look healthier than it is.

## 10. File-Level Change Plan

### 10.1 Add

- `backend/app/services/patient_read_service.py`

### 10.2 Modify

- `backend/app/api/v1/patients.py`
- `backend/app/services/patient_module_proxy.py` if small mapping helpers are needed
- `backend/tests/test_patient_module_proxy.py` only if proxy parameter coverage needs extension
- add new tests for the read adapter and patient API behavior

The platform patient API should stop being a pure router re-export and instead become the explicit platform read entrypoint for this phase.

## 11. Testing Strategy

This step should add four categories of tests.

### 11.1 Read Adapter Tests

Verify that:

- the adapter uses the compatibility reader when the flag is off
- the adapter uses `PatientModuleProxy` when the flag is on
- the adapter constructs `PatientModuleContext` correctly

### 11.2 Patient API Tests

Verify that:

- list and detail responses keep the same outward response shape
- the platform patient API delegates to the read adapter rather than raw router imports

### 11.3 Proxy Path Tests

Verify that:

- the correct token and parameters are sent to `PatientModuleProxy`
- list and detail parameter mapping stays correct

### 11.4 Flag Behavior Tests

Verify that `PATIENT_MGMT_READ_FROM_SERVICE` is not dead configuration and actually selects the execution path.

## 12. Rollout and Success Criteria

This step is complete when all of the following are true:

- `PATIENT_MGMT_READ_FROM_SERVICE` controls the patient read path
- platform patient list and detail reads can run through `PatientModuleProxy`
- the platform response format for list and detail is unchanged
- the compatibility read path remains available when the flag is off
- no write behavior changes are introduced in this step
- targeted read-cutover tests pass
- full backend test suite still passes

## 13. Risks and Follow-Up

This design intentionally leaves several items for the next step:

- write-path cutover
- removal of the compatibility read path
- broader dual-write orchestration outside repository-level support
- platform-admin edge cases during the legacy fallback period

Those are deferred on purpose. The goal of this step is to make read cutover explicit and reversible before touching write ownership.
