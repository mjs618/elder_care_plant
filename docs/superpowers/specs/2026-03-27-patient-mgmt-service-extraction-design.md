# Patient Management Service Extraction
Date: 2026-03-27
Status: Draft for review

## 1. Background

The platform control plane has now been consolidated around tenant entitlements, module catalog records, and deployment metadata. The next step is to extract one business module into a real independently deployable service.

`patient_mgmt` is the right pilot because it already has:

- a dedicated package under `backend/modules/patient_mgmt`
- its own API router and service entrypoint
- event subscriber scaffolding
- a Dockerfile for standalone execution

The current implementation still depends on the platform runtime for tenant database context, permission gating, and shared ORM access. That makes it a modular monolith in practice, even though the service shape already exists on disk.

This document defines the first module extraction phase: move `patient_mgmt` from in-process module hosting to independently deployable service ownership.

## 2. Problem Statement

The current `patient_mgmt` module is not independently deployed in the architectural sense, even though it can be launched separately.

### 2.1 Runtime Coupling

The module API routes still depend on platform-provided dependencies such as tenant-scoped database access and permission checks. That means the module cannot fully own its request context.

### 2.2 Data Coupling

Patient data is still modeled inside the same backend codebase and migration flow as the platform. The module needs its own data store and schema lifecycle to satisfy the target architecture.

### 2.3 Event Coupling

The module already emits and consumes events, but the event integration is still coupled to the shared codebase and shared runtime assumptions. Those contracts need to become service-level integration points rather than in-process helpers.

### 2.4 Deployment Coupling

The platform still mounts business module routers through the main application. That prevents `patient_mgmt` from becoming an independently deployable service with a clear operational boundary.

## 3. Goals

This phase must achieve the following:

- extract `patient_mgmt` into a separately deployable service
- preserve the module's existing API behavior for current consumers during migration
- give the module its own data store and migration path
- remove the module's direct dependency on platform internal dependency helpers
- keep entitlement and identity enforcement aligned with the control plane
- preserve the current event-driven patterns for patient lifecycle events

## 4. Non-Goals

This phase does not require:

- extracting `assessment`
- redesigning the entire shared frontend shell
- replacing the control plane
- rewriting patient business rules from scratch
- removing all compatibility shims on day one

The first module extraction should be a controlled migration, not a second redesign of the whole platform.

## 5. Target Architecture

The target architecture for `patient_mgmt` has four parts.

### 5.1 Platform Control Plane

The platform remains the control plane and continues to own:

- authentication
- tenant lifecycle
- subscription plans
- tenant entitlements
- module catalog and deployment metadata

The control plane decides whether a tenant may use `patient_mgmt`, but it does not execute patient business logic.

### 5.2 Patient Management Service

`patient_mgmt` becomes an independently deployable FastAPI service.

It is responsible for:

- patient CRUD
- patient search and detail access
- patient lifecycle events
- patient-specific validation and response schemas
- its own health endpoint
- its own runtime and deployment packaging

The service exposes its own router and entrypoint and no longer relies on the platform main app to mount its router.

### 5.3 Request Context Boundary

The patient service must receive identity and tenant context through explicit runtime inputs, not by importing platform dependency functions directly.

The platform may continue to gate access at the control plane boundary, but the module service should be able to validate:

- which tenant the request belongs to
- which user is acting
- whether the module is entitled for that tenant

### 5.4 Event Boundary

The patient service continues to publish domain events such as:

- patient created
- patient updated
- patient deleted

It may also subscribe to relevant upstream events, but event handling must be isolated behind the module service boundary rather than hardwired into platform internals.

## 6. Module Boundary

The first extraction phase should keep the following inside the patient service:

- `Patient` domain behavior
- patient request and response schemas
- patient API routes
- patient event publishers
- patient event subscribers
- patient-specific health checks

The following should stay in the platform control plane:

- auth token issuance
- entitlements
- module discovery
- module deployment records
- tenant subscription and plan state

The module service may depend on the control plane through contracts, but it must not depend on the control plane's internal ORM or database tables.

## 7. Data Boundary

`patient_mgmt` must own its data store.

That means:

- patient tables live in the module service schema or database
- module migrations are executed independently from platform migrations
- patient service tests should not require the platform database schema to represent patient behavior

The platform may still hold compatibility data during transition, but it should not remain the primary owner of patient business records.

The migration approach should support a transitional period where read traffic or selected write traffic can still be proxied, but the end state is a module-owned persistence boundary.

## 8. Runtime Boundary

The extraction must enforce one clear runtime rule:

- the platform decides whether a tenant can access `patient_mgmt`
- the patient service handles the request if it is routed there

The module should no longer import platform helpers such as tenant-scoped DB session builders or permission gates.

Instead, the module should accept a service-level context contract that can be supplied by:

- a gateway
- a platform proxy
- a local compatibility wrapper during migration

At minimum, that context contract should carry:

- tenant identity
- user identity
- user scope or role context
- request correlation metadata
- a proof that the platform already authorized access to `patient_mgmt`

## 9. Migration Strategy

The migration should happen in four steps.

### Step 1: Extract the Service Entry

Keep the module's standalone `main.py` as the primary runtime target.

The goal of this step is:

- make the module service start cleanly on its own
- keep `/health` and module router registration working
- preserve current request behavior as much as possible

The platform may keep a compatibility path while the standalone service is verified.

### Step 2: Replace Platform Dependency Imports

Remove the module's direct dependency on platform helper functions.

The module should stop importing:

- platform tenant DB context helpers
- platform permission dependency helpers

Instead, it should consume a module-local request context contract.

### Step 3: Split the Data Store

Move patient data ownership into the module service.

The implementation should include:

- module-local migrations
- module-local schema or database ownership
- module-local tests that operate against the module data model

### Step 4: Cut Over Traffic and Remove Compatibility Shims

Once the module service is stable:

- point the platform deployment metadata at the module service
- route requests to the external service
- retire direct in-process mounting for this module

The platform control plane should remain the source of entitlement truth throughout the cutover.

## 10. Recommended Delivery Order

The recommended order is:

1. make the standalone patient service the real runtime target
2. replace platform dependency imports with explicit context contracts
3. move patient persistence ownership into the module service
4. switch platform routing to the external service
5. remove the old in-process compatibility path

This order minimizes risk. If the data split happens before the runtime contract is stable, the module will be harder to debug and easier to break during cutover.

## 11. Testing Strategy

This extraction should be backed by tests at three levels:

- service-level tests for patient CRUD and validation
- contract tests for module routing and request context expectations
- integration tests for entitlement-driven access and event publication

Key behaviors to verify:

- the standalone module app boots successfully
- the module routes still satisfy current API behavior
- patient events are emitted with the expected payload shape
- the module no longer requires direct platform helper imports
- the control plane still governs whether the tenant can use the module

## 12. Risks

The main risks are:

- duplicating auth logic between the platform and the module service
- keeping two sources of truth for patient data too long
- breaking the current frontend or admin flows during traffic cutover
- leaving event handlers coupled to platform-only types

These risks are acceptable only if the migration stays incremental and the compatibility boundary is explicit.

## 13. Decision

`patient_mgmt` should be the first independently deployed business module.

The system should not wait for a perfect multi-service platform before extracting it. The correct move is a controlled pilot extraction that proves the control plane can orchestrate a real external module service.

The next document after approval of this spec should be an implementation plan for Phase 2 Step 1: extract the patient service entry and runtime boundary.
