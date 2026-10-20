# Data and privacy policy

Every commit and issue attachment must be safe to publish.

## Allowed

- Hardware class and public driver/runtime version numbers.
- Synthetic scripts and generated-input checksums.
- Short error excerpts after removing personal paths and identifiers.
- Aggregated timing, throughput, and memory figures.

## Remove before publishing

- User names, home directories, workspace/repository paths, and host names.
- IP/MAC addresses, device UUIDs, serial numbers, account IDs, tokens, and API keys.
- Full Windows Event Log exports, raw WSL log bundles, and screen recordings.
- Any training data, model material, prompts, user content, or private source code.

When uncertain, keep the artifact out of Git and summarize it in a redacted
note. Upstream maintainers can request protected logs through their documented
channels if the issue reaches that stage.
