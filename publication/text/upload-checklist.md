# Local preparation and upload checklist

These materials are prepared locally. No repository, release, or social post has been published by this preparation step.

## Source-only GitHub upload

The prepared GitHub folder is source-only. The Windows ZIP is a local personal testing artifact. Upload source and publication images first; the binary steps below apply only if a public executable release is later chosen.

## Before public upload

- [ ] Confirm the owner, repository name, copyright identity, and real repository URL. Do not invent these in copy.
- [ ] Run Windows tests and a real-device capture / playback check; verify both languages, restart persistence, file import, saved phrases, and extracted executable startup.
- [ ] Confirm screenshots show the final v0.8 build and only audio cleared for public use.
- [ ] Include LICENSE, THIRD_PARTY_NOTICES.md, and all dependency notices / license files in the Windows archive.
- [ ] Prepare and retain the exact corresponding source and build instructions for the distributed application and GPL components, including Pedalboard / Rubber Band and the bundled Gyan FFmpeg 7.1 build and its enabled libraries. A link to an upstream project alone is not a substitute for fulfilling the applicable source-distribution conditions.
- [ ] Review Qt LGPL redistribution details for the actual package, including replacement / relinking, notices, and access to corresponding Qt sources; preserve shared libraries.
- [ ] Check the actual packaged component inventory against THIRD_PARTY_NOTICES.md. Resolve any missing source, notices, or licenses before public binary distribution.
- [ ] Package the whole RiffTonic folder, verify the archive, and generate its SHA-256 checksum.
- [ ] Publish the source snapshot. If choosing to distribute a public binary after the above checks, create a v0.8 release with the bilingual notes, Windows archive, checksum and matching source materials.
- [ ] Replace download references in social copy only after the release URL exists. Upload platform-specific images and proofread the final preview.

## License strategy

The project source is designated GPL-3.0-or-later to support a GPL-compatible distribution alongside Pedalboard. The copied LICENSE is the unmodified GPL v3 text from the installed Pedalboard distribution. This designation does not relicense dependencies or automatically discharge binary-distribution obligations. The installed FFmpeg executable reports GPL and version3 enabled. This checklist records engineering release work still needed for public distribution, rather than a legal opinion or a claim of completed compliance.

## CI scope and references

CI uses Windows, Python 3.14, pip requirements, and unittest discovery of `test_*.py`, with Qt offscreen. It does not exercise a physical audio device. The workflow is prepared locally; a successful GitHub Actions run cannot be claimed until the repository is uploaded and the workflow actually runs.

Official action references: [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python). Stable supported major versions v4 / v5 are used.
