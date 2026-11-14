# Security Policy

## Project status

ActRun is experimental software under active development.

The current implementation is not designed to provide a production security boundary. In particular, registered Python tools execute inside the same process as the runtime and inherit that process's permissions.

Do not rely on the current implementation to safely execute untrusted code, isolate credentials, restrict network access, or protect production systems.

## Supported versions

Until ActRun publishes its first stable release, security fixes will generally target the latest version on the default development branch.

There is currently no long-term support policy for older versions.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in public issues, pull requests, or discussions.

Use GitHub's **Private vulnerability reporting** feature for this repository if it is enabled.

If private vulnerability reporting is unavailable, contact the repository maintainers privately through their GitHub profile before sharing technical details publicly.

When reporting a vulnerability, include:

- A description of the issue.
- The affected component or file.
- Steps to reproduce the issue.
- The potential security impact.
- A proof of concept, if available.
- Any suggested mitigation.

Do not include real credentials, private keys, customer data, or confidential production logs in a report.

## What to report

Examples of security issues include:

- Unauthorized tool execution.
- Unexpected execution of unregistered tools.
- Code execution vulnerabilities.
- Path traversal or unsafe file handling.
- Exposure of credentials or sensitive data.
- Incorrect handling of untrusted input that creates a security impact.
- Vulnerabilities in dependencies that materially affect ActRun.

General questions, feature requests, and non-security bugs should be reported through the regular issue tracker.

## Response process

The maintainers will make a reasonable effort to:

1. Acknowledge receipt of a private report.
2. Reproduce and assess the reported issue.
3. Determine the affected versions and potential impact.
4. Develop and test a fix where appropriate.
5. Coordinate disclosure with the reporter.

Response times are not guaranteed while the project is in its early development stage.

## Security limitations of the current implementation

The current prototype does not provide:

- Process or container isolation for tools.
- Credential isolation.
- Network egress restrictions.
- A permission model beyond registered tool names.
- Independent validation of tool arguments against their declared parameter schemas.
- Guaranteed redaction of sensitive information in event logs.
- A hardened multi-tenant execution environment.

These limitations are important. A tool registered with ActRun can perform any action permitted to the Python process in which it runs.

## Responsible disclosure

Please allow maintainers a reasonable opportunity to investigate and address a vulnerability before publishing technical details that could enable exploitation.

We appreciate responsible security research and clear, reproducible reports.

