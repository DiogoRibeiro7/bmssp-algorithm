# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| main    | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do not** open a public GitHub issue.
2. Use [GitHub Security Advisories](https://github.com/DiogoRibeiro7/bmssp-algorithm/security/advisories/new) to report the vulnerability privately.
3. Include a clear description of the issue, steps to reproduce, and potential impact.

You can expect an initial response within 7 days. We will work with you to understand the issue and coordinate a fix before any public disclosure.

## Scope

This is a research algorithm repository. Security concerns are most likely to involve:

- Malicious DOT file input causing crashes or memory corruption (C implementation)
- Denial of service through crafted graphs causing excessive computation
- Dependencies with known vulnerabilities
