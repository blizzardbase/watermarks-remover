# Mark classes

## Invisible Unicode

These characters can be accidental, required for language shaping, or used as
an edit based carrier. Inspection reports all suspicious classes. Default
cleaning removes only the narrow safe set documented in `SKILL.md`.

## File provenance metadata

PNG, JPEG, SVG, DOCX, ODT, HTML, and Markdown can contain machine readable
provenance or generator fields. Default cleaning is targeted and preserves
unrelated metadata. PDF is inspection only.

## Statistical text signals

A statistical signal can live in word choice rather than a character or file
field. This skill has no detector for that class and makes no removal claim.
An ordinary rewrite can change wording, but it can also change meaning.

## Media signals and soft binding

An image, audio, or video signal can live in the content rather than metadata.
Removing file metadata does not remove such a signal. This skill has no media
signal detector or remover.

## Private and training based signals

Private vendor detectors, secret keyed systems, and model training backdoors
are outside scope.
