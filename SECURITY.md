# Security Policy

## Scope

DataSense is a local-first analytics application. Security work focuses on protecting user datasets, credentials, generated evidence, packaged binaries, and optional network integrations.

## Supported versions

Security fixes should target the current `main` release line. Older release lines may receive fixes only when the issue is severe and the remediation is low-risk to backport.

## Reporting a vulnerability

Do not disclose sensitive details in a public issue. Report the affected component, impact, reproduction steps, and any relevant logs with secrets/redacted values removed through a private maintainer security channel.

## Security boundaries

- Local analytics must not transmit dataset contents unless the user explicitly activates a documented external integration.
- API keys, tokens, private keys, and passwords must never be written to logs, reports, lineage, or evidence payloads.
- Governance evidence is metadata-first and should avoid raw sensitive values.
- External actions must remain behind explicit user-controlled boundaries and should fail closed on invalid authorization or policy state.
- Release binaries should be accompanied by checksums and verifiable build provenance.

## Supply-chain controls

Pull requests should receive dependency review before merging. Release workflows should generate artifact provenance attestations for distributable binaries and archives. Attestations establish build provenance; they do not by themselves prove that the artifact is secure.

## Security testing priorities

1. Sensitive-data redaction and local-only behavior.
2. Credential handling and optional cloud/AI integrations.
3. Persisted project/report integrity.
4. Dependency vulnerabilities and license policy.
5. Packaged Windows executable and installer provenance.
6. Database/SQL input handling and filesystem boundaries.
