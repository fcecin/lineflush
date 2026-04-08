# Sample scripts

Build and test helper scripts for [Logos Delivery](https://github.com/logos-messaging/logos-delivery), a Nim project using nimble and make. These demonstrate `lineflush` usage and also include some standalone conveniences.

These worked at the time of commit [f5762af4](https://github.com/logos-messaging/logos-delivery/commit/f5762af4c4834972d98cdda961b796c7e30613bf) in the logos-delivery repo.

## Build scripts

| Script | Description |
|--------|-------------|
| `nmake` | Build the main binary (`wakunode2`) |
| `nmakew` | Build `libwaku` |
| `nmakel` | Build `liblogosdelivery` |
| `nmake3` | Build all three targets |

All build scripts accept `-j N` for parallel compilation (e.g. `nmake -j22`).

On first run after a nuke, if `~/localdeps` exists, nimble dependencies are
restored from that cache instead of downloading from GitHub.

## Test scripts

| Script | Description |
|--------|-------------|
| `ntest` | Run all test suites |
| `ntest common` | Run testcommon suite only |
| `ntest waku` | Run testwaku suite only |
| `ntest node` | Run testwakunode2 suite only |
| `ntest <substr>` | Find and run a single test file by substring match |

## Cleanup scripts

| Script | Description |
|--------|-------------|
| `nclean` | Light clean: remove `build/` and `nimcache/` only |
| `nnuke` | Full nuke: clean everything and re-init git submodules |
| `nfullnuke` | Nuke + wipe the global nimble cache (`~/.nimble/pkgs2`) |

## Dependency cache

| Script | Description |
|--------|-------------|
| `nlocaldeps` | Snapshot current `nimbledeps/` to `~/localdeps` |
