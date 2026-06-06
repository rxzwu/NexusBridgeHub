# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-06

### Added

- Package **nexusbridgehub** (rebrand from NexusBridge — PyPI name was taken)
- WebSocket bridge server (`nexusbridgehub-server`)
- Worker client (`BridgeClient`) and controller (`BridgeController`)
- Thin worker app with pair-code flow (`nexusbridgehub-worker`)
- JWT auth, pair codes, encrypted server URL for builds
- CLI: `nexusbridgehub-build` for distributable worker bundles
- Minimal RU/EN examples and integration templates
- Error handling with auto-reconnect; worker survives handler failures
- CI on Python 3.11–3.14
- Documentation: README (EN/RU), DEPLOY.ru.md, TESTING.ru.md

[0.1.0]: https://github.com/rxzwu/nexusbridgehub/releases/tag/v0.1.0
