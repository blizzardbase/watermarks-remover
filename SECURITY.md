# Security policy

## Supported version

Security fixes target the latest code on `main`. Installations should use an
exact reviewed commit from the Blizzardbase fork.

## Private reporting

Do not open a public issue for a vulnerability. Use
[GitHub Security Advisories](https://github.com/blizzardbase/watermarks-remover/security/advisories/new)
and include impact, reproduction steps, and the affected commit.

## Important report classes

1. A path escape or unintended file overwrite.
2. A symbolic link bypass.
3. Resource exhaustion on a crafted file or archive.
4. A network, process, credential, or installer path in the installed skill.
5. Corruption or deletion of legitimate document content under default use.
6. Exposure of private file content through output or diagnostics.

Third party detector accuracy and requests to evade disclosure are outside the
security scope. The ethical use boundary is documented in
`skills/remove-ai-marks/references/ethics.md`.

Good faith research that avoids privacy harm, service disruption, and data
destruction is welcome. Coordinate disclosure until a fix is available.
