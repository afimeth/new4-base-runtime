# New4 / SAML 2.0 — executable example frame

This is a **small, independent reference example**, not a SAML login integration. A Go standard-library program emits a SAML 2.0 service-provider-initiated **AuthnRequest XML** with a fresh 128-bit request ID and UTC timestamp. It also demonstrates **unsigned HTTP-Redirect binding** using raw DEFLATE, Base64 and URL encoding. All endpoints use the non-operational example.invalid domain, and the program never sends requests.

## Run and verify (from repository root)

    go run ./examples/saml-frame
    go test ./examples/saml-frame -v
    go test ./...

The current GitHub Actions workflow runs Go tests by way of scripts/go_evaluate.py, although its older pinned Go evidence file predates this example. New tests must be judged by their new CI run/commit, not retroactively credited to older receipts.

## One identity protocol; several frame representations

| File | Purpose | Runtime status |
| --- | --- | --- |
| [frame.json](frame.json) | Strict SP/IdP configuration and explicit no-authority marker | Embedded and validated by Go |
| [frame.yaml](frame.yaml) | Human-readable projection of identical configuration | Documentation only; no YAML loader |
| [frame.toml](frame.toml) | Alternative human-readable projection | Documentation only; no TOML loader |
| [authn-request.xml](authn-request.xml) | Reproducible fixed-time SAML request fixture | Matched byte-for-byte by tests |
| [sp-metadata.xml](sp-metadata.xml) | Illustrative service-provider metadata | Test checks consistency; not deployable |
| [frame.go](frame.go), [main.go](main.go), [frame_test.go](frame_test.go) | Executable XML generation, Redirect encoding, negative/fixture tests | Go 1.22+, no third-party dependencies |

SAML is an XML-based federation protocol; JSON Schema, YAML and TOML are not replacements for it. Here they express a bounded **configuration view** while Go implements the sample message framing.

## Explicit trust boundary (fail closed)

    frame.json -> Go -> unsigned samlp:AuthnRequest XML
                           |
                           +--> illustrative SAMLRequest Redirect URL
                                  (no network / IdP connection)

    Incoming Response / Assertion: NOT IMPLEMENTED
    Signature and certificate verification: NOT IMPLEMENTED
    Request-response correlation and replay defense: NOT IMPLEMENTED
    Principal-to-New4 authority mapping: NOT IMPLEMENTED
    ownerauth or other effect approval: DENIED

This implementation neither accepts a SAML Response nor creates a user session or authorizes an action. A production SP would need authenticated IdP trust configuration, secure XML signature verification (including wrapping resistance), metadata/key rotation, strict Recipient/Destination/Audience/InResponseTo/time checks, replay protection, session handling and signed requests if required by its IdP. Never treat an identity assertion as New4 owner authorization without a separately verified policy/authority gate.

The metadata and URLs are synthetic and **must not** be imported into a live IdP. Passing these fixture tests is not proof of enterprise SSO, production integration, compliance, or a security audit. There are no private keys, credentials, customer records or remote services.

Standards and guidance: [OASIS SAML 2.0 Technical Overview](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-tech-overview-2.0.html) · [OWASP SAML Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet)
