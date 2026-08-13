# Removal matrix

| Target | Default action | Broad option | Main risk |
| --- | --- | --- | --- |
| Soft hyphen, zero width space, byte order mark | Remove | None | An intentional character can be lost |
| Joiners, direction controls, tags, variation selectors | Preserve | `--aggressive-unicode` | Language shaping or emoji can change |
| Special spaces | Preserve | `--normalize-spaces` | Nonbreaking layout can change |
| Lookalike letters | Preserve | `--aggressive-homoglyphs` | A legitimate script can change |
| Unicode compatibility forms | Preserve | `--nfkc` | Visual or semantic distinctions can change |
| PNG and JPEG matching metadata | Remove | `--strip-all-metadata` | Unrelated metadata can be lost |
| SVG matching metadata blocks | Remove | None | Matching metadata is lost |
| DOCX matching property values | Clear | None | Application attribution is lost |
| DOCX custom XML | Preserve | None | A residual marker can remain |
| ODT matching generator or creator | Remove | None | Matching attribution is lost |
| HTML matching meta and JSON LD fields | Remove | None | Matching page metadata is lost |
| Markdown matching frontmatter keys | Remove with nested children | None | Matching build metadata is lost |
| PDF | Inspect only | None | Cleaning requires a separate audited tool |

The scripts do not inspect or remove statistical text marks, pixel marks,
audio marks, video marks, soft binding, private vendor signals, or model
training backdoors.
