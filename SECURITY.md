# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of CutFlow very seriously.

If you believe you have found a security vulnerability in CutFlow (such as an unintentional API key exposure, remote code execution risk, or input validation flaw in file upload handling), please **do not report it via a public GitHub issue**.

### Reporting Guidelines

Please report security issues via GitHub Private Vulnerability Reporting on our repository, or send an email to:
`security@cutflow.dev` (or open a confidential security advisory).

Please include:
1. A description of the vulnerability and its potential impact.
2. Steps or a minimal proof of concept to reproduce the issue.
3. Any proposed mitigations or fixes.

We will acknowledge receipt of your vulnerability report within 48 hours and provide updates on resolution timeline.

### Zero-Tolerance on Hardcoded Secrets

CutFlow follows a strict policy: **no secrets or API keys may ever be hardcoded** in client bundles, repository commits, or documentation. All API keys must be loaded from local environment variables (`.env`) or securely supplied by the user at runtime in browser storage.
