# Platform Control Plane Redesign

Date: 2026-03-27
Status: Draft for review

## 1. Background

The original product goal is:

- Deploy the platform management layer independently from business modules.
- Let customers purchase plans that grant access to different pluggable modules.
- Allow each business module to be deployed independently and upgraded independently.
- Give each business module its own data store instead of sharing the platform database.

The current implementation does not fully match that goal. It behaves as a modular monolith:

- The main FastAPI app mounts module routers inside the same process.
- Module registration is handled by an in-process singleton registry.
- Runtime authorization is split across plan fields, tenant module activation, and global module switches.
- Platform data and module business data are still modeled inside one backend domain.

This document defines the target architecture and the migration path required to bring the system back toward the original goal.

## 2. Problem Statement

The current system has drifted from the intended architecture in four structural areas.

### 2.1 Control Plane Drift

The platform currently acts as both control plane and business host. It manages tenants, plans, auth, and module settings, but it also imports and mounts business module routers directly.

This makes the platform a runtime container for modules instead of a control layer above modules.

### 2.2 Deployment Drift

Modules are not truly independently deployable today. Even though module folders exist, the main app still owns module loading and routing. That means deployment boundaries are organizational only, not runtime boundaries.

### 2.3 Data Boundary Drift

The target model requires each business module to own its own data store. The current codebase still treats module data as part of the same application domain and persistence layer.

### 2.4 Authorization Drift

The system currently mixes multiple sources of truth:

- `SubscriptionPlan.included_modules`
- tenant-level module activation state
- global module switch state

These concepts are not unified into one runtime entitlement model. As a result, package design, tenant activation, and runtime permission checks can diverge.

## 3. Goals

The redesign must achieve the following:

- Make the platform a standalone control plane.
- Make business modules independently deployable.
- Ensure each business module owns its own data store and schema lifecycle.
- Define a single source of truth for tenant entitlements.
- Keep a unified tenant-facing entry experience while allowing module backends to live outside the platform runtime.
- Preserve the existing auth, tenant, and admin concepts where they still fit the new model.

## 4. Non-Goals

This redesign does not require:

- Rewriting all business logic immediately.
- Splitting every existing feature into a standalone service in one release.
- Replacing the current frontend shell with a micro-frontend platform in phase one.
- Turning the system into a full microservice mesh before the control plane is stable.

## 5. Target Architecture

The system should be divided into four layers.

### 5.1 Platform Control Plane

The platform control plane is a standalone service responsible for:

- authentication and token issuance
- users, roles, and permissions
- tenant lifecycle
- subscription plans
- tenant subscriptions
- module catalog
- module deployment records
- tenant entitlements
- module discovery metadata exposed to the frontend

The control plane must not host patient, assessment, or other business-domain data.

### 5.2 Business Module Services

Each module becomes an independently deployable service. Examples include:

- patient management service
- assessment service

Each module service is responsible for:

- its own business API
- its own domain logic
- its own data store
- its own migrations
- consuming platform-issued identity and entitlement context

The platform must stop mounting module routers in-process once a module is migrated.

### 5.3 Integration Layer

Platform and modules communicate through explicit contracts:

- synchronous API calls for immediate queries and commands
- asynchronous events for cross-module workflows and eventual consistency

Modules must not depend on the platform's internal ORM models or internal tables.

### 5.4 Frontend Shell

The frontend remains a unified shell in the near term. It should:

- authenticate against the control plane
- fetch the current tenant's module availability from the control plane
- receive module metadata, availability, and entry information from the control plane
- route the user only to modules the tenant is entitled to use

The frontend should gradually stop assuming that every business API sits behind the same `/api/v1` backend origin.

## 6. Domain Model

The target control plane should keep and add the following concepts.

### 6.1 Keep

- `Tenant`
- `SubscriptionPlan`
- `User`
- `Role`
- `Permission`

These concepts are still valid, but they need cleaner responsibilities.

### 6.2 Add

#### `TenantSubscription`

Represents what a tenant currently purchased.

Fields should cover:

- tenant id
- plan id
- subscription status
- effective start
- renewal or expiration timestamps

This models the commercial relationship instead of forcing package information directly into runtime authorization.

#### `ModuleCatalog`

Represents the list of modules the platform knows about.

Fields should cover:

- module slug
- display metadata
- module type
- sellable flag
- globally enabled flag
- supported capability metadata

This replaces the current overloading of system-level module records.

#### `ModuleDeployment`

Represents where and how a module is currently deployed.

Fields should cover:

- module slug
- environment
- base URL or service endpoint
- deployed version
- health status

This is required once modules become independently deployable services.

#### `TenantEntitlement`

Represents the final runtime authorization result for a tenant.

Fields should cover:

- tenant id
- module slug
- entitlement status
- source of grant
- effective timestamps

This becomes the runtime source of truth for whether a tenant can use a module.

### 6.3 Redefine Existing Concepts

#### `included_modules`

This should remain only as a plan template concept if retained at all. It can express default packaged capabilities, but it must not be the runtime source of truth.

#### tenant module activation

The current tenant module table should be deprecated or reduced to a transitional compatibility layer. It should not remain the long-term core authorization model.

#### system module records

The current system module concept mixes directory metadata, switch state, version data, and deployment concerns. Those responsibilities should be split between `ModuleCatalog` and `ModuleDeployment`.

## 7. Authorization Model

The redesign must establish one clear runtime rule:

- plan data describes commercial packaging
- subscription data describes what the tenant bought
- entitlement data describes what the tenant can actually use right now

Runtime module access checks must resolve against tenant entitlements, not against scattered combinations of:

- plan template fields
- tenant activation toggles
- global module switches

Permission checks should be layered:

1. Is the tenant entitled to the module?
2. Is the module globally enabled and available?
3. Does the current user have the required permission inside that module?

This order prevents commercial state, operational state, and user-level RBAC from being conflated.

## 8. Migration Strategy

The migration should happen in three phases.

### Phase 1: Control Plane Consolidation

Objectives:

- define the control plane as the only source of tenant, plan, subscription, and entitlement truth
- add the missing control plane domain models
- unify module discovery and authorization outputs

Key outcomes:

- the platform can tell the frontend which modules a tenant can use
- the platform can expose module endpoints and metadata without hosting module code
- authorization logic is based on tenant entitlements

### Phase 2: Module Runtime Decoupling

Objectives:

- stop treating business modules as in-process routers of the platform app
- migrate `patient_mgmt` and `assessment` first as pilot services
- give each pilot module its own data store and migration path

Key outcomes:

- the platform no longer imports and mounts those module routers directly
- each pilot module can be deployed and upgraded independently
- platform-to-module communication uses contracts instead of internal imports

### Phase 3: Frontend Assembly Upgrade

Objectives:

- keep the unified shell but make it driven by control plane metadata
- remove hard assumptions that all business APIs live behind the same backend runtime

Key outcomes:

- frontend routes and module navigation are assembled from control plane responses
- module entry metadata becomes deployable-system aware
- the shell remains consistent even while modules live in different services

## 9. Recommended Delivery Order

The recommended order is:

1. redesign the control plane domain model
2. unify runtime authorization around tenant entitlements
3. decouple module runtime loading from the platform process
4. migrate one or two modules as independent services
5. upgrade frontend module assembly to consume the new control plane outputs

This order is intentional. If module extraction starts before the control plane model is fixed, the team will duplicate authorization logic across services and create a messier system than the current one.

## 10. Why This Is a Redesign, Not a Full Rewrite

A full rewrite is not required yet because the current codebase still contains useful assets:

- authentication flows already exist
- tenant and plan concepts already exist
- module-aware frontend navigation already exists in early form
- module contracts and event-driven direction have already been explored

What needs replacement is not the entire codebase. What needs replacement is the architectural center of gravity:

- from in-process module hosting
- to control-plane-driven module orchestration

## 11. Decision

The system has drifted from the original goal of an independently deployed control plane with independently deployed, independently stored business modules.

The correct response is:

- do not continue expanding the current modular monolith as if it were the target architecture
- do not immediately discard the whole codebase
- perform a control plane redesign first
- migrate toward independent module services in phases

The next document after approval of this spec should be an implementation plan for Phase 1: control plane consolidation.
