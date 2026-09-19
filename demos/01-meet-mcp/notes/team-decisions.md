# Team Decisions

A short log of decisions the team has agreed on, newest first.

## 2026-09-18: Container Apps for the storefront

We moved the storefront from virtual machines to Azure Container Apps. Revisions
give us gradual traffic shifting and fast rollbacks without extra tooling.

## 2026-08-04: Squash merges only

Pull requests are squash merged so each release tag maps to a readable history.

## 2026-06-12: Release from main

Releases are tagged from `main`. Long-lived release branches are no longer used.
