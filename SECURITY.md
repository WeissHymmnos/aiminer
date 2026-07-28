# Security Policy

## Reporting a Vulnerability

If you discover a security issue in AI Alpha Miner, please **do not** open a
public GitHub issue.

Instead, email the maintainers privately (or open a private security advisory
on GitHub if the repository has that feature enabled) with:

- A description of the issue and its impact
- Steps to reproduce (PoC if available)
- Affected versions / commit hashes if known

We aim to acknowledge reports within 7 days.

## Secrets and credentials

Never commit real API keys, RiceQuant tokens, or `.env` files.

- Copy `.env.example` → `.env` and fill in local credentials.
- Rotate any key that may have been committed historically.
- Prefer short-lived tokens where the provider supports them.

## Code execution surface

Factor expressions are evaluated through a restricted operator set and an AST
transformer (`SafeEvalTransformer`). Treat any relaxation of that whitelist as
security-sensitive and review carefully before merging.

## License note

This project is AGPL-3.0-only. Security patches must remain under the same
license; do not propose dual-licensing or proprietary exception patches via
public issues without maintainer agreement.
