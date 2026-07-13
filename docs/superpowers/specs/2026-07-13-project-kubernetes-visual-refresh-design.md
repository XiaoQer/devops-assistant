# Project Kubernetes Visual Refresh Design

## Purpose

Improve the Project Kubernetes page's density, hierarchy, and operational clarity without changing
cluster behavior. The accepted visual direction is a responsive two-column resource-card layout, with
matching onboarding choices and form sections.

## Page Hierarchy

The page header remains the source of Project context, description, refresh, and add actions, but uses
less vertical space. The cluster surface begins closer to the header and avoids a second oversized title
hierarchy. A compact section header reports the resource purpose and cluster count.

## Cluster Cards

At wide content widths, clusters render in two equal columns; at narrower widths they collapse to one.
Each card uses four layers:

1. Identity: cluster name, environment label, and Default marker.
2. Connection endpoint: a contained, neutral API Server panel with context as supporting text.
3. Runtime facts: connection state, Kubernetes version, active state, and Namespace Prefix as compact
   semantic badges.
4. Footer: last-test time and operational actions.

“Test connection” is the primary visible action and “Edit” is secondary. “Set default” and “Delete” move
into an Element Plus overflow dropdown. Delete continues through the existing confirmation dialog.

## Onboarding Choice

The add dialog retains two path cards. The available existing-cluster path receives the stronger border,
icon treatment, and directional affordance. Aliyun initialization remains disabled with subdued contrast
and an explicit “Coming soon” badge. Both cards share the same radius and spacing as cluster resources.

## Form Dialog

The existing form becomes three visual groups:

- Basic information: name, environment label, description.
- Connection configuration: kubeconfig, context, Namespace Prefix, and transient test feedback.
- Governance settings: default and active switches.

The kubeconfig textarea uses a monospace stack, compact line height, and a slightly tinted code-surface
background. Footer actions retain the existing behavior and remain visually separated from scrolling
content through the shared dialog base.

## Responsive Behavior

The two-column resource grid collapses at approximately 1100px of available content width. Card headers
and footers wrap without reordering the information hierarchy. On mobile widths, action buttons remain
full labels and the overflow control stays reachable.

## Scope and Verification

The change is local to `ProjectKubernetesSettings.vue` unless a verified limitation requires a minimal
shared-style adjustment. No API, type, route, state, validation, or persistence behavior changes.
Verification consists of frontend type checking and production build, full `./scripts/verify.sh`, and
visual inspection at wide and narrow widths.
