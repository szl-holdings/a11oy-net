# Header rollout script compatibility

## Invariant before the change

Every HTML page published by this repository must keep its intended scripts
executable under the committed catch-all `_headers` policy. A page outside the
homepage's explicit metadata checks must not silently escape this validation.
The script policy remains `self` plus the two exact homepage hashes. No inline
execution wildcard, evaluation permission, remote script origin, or new network
destination is added.

At reviewed source `80db11538bc17f178b43f22e992382d39cfe4db9`, all 50 HTML
blobs were read and matched to their Git object identifiers. Two inline script
blocks were outside the catch-all policy: `ayllu/index.html` and
`khipu/index.html`. This is compatibility evidence for deploying that policy;
it does not assert that a live response header is currently enforced.

The subsequent Atelier repair moved protected main to
`35f64d4235253992f32e4806aec55fbfb777044c`. The complete recursive tree and commit
comparison confirm that all 50 HTML blobs, `_headers`, and every existing path
changed by this candidate are identical at that new base.

## Correction and validation

The two existing script bodies move byte-for-byte to same-origin JavaScript
files. Their script tags keep the same position and synchronous execution order.
The page content, visual behavior, links, and header values stay the same.

The existing header validator also checks every HTML file beneath the source
root, excluding top-level `.git` and `.github`, which the Pages builder excludes. It
rejects unadmitted inline hashes, inline event/JavaScript URL attributes and
script origins outside the existing policy. Script bodies and source attributes
are parsed as HTML, so `data-src` is never mistaken for `src`. Duplicate
attributes, ambiguous script/comment markup or URLs, cross-origin bases, and
iframe `srcdoc` fail pending a separate explicit contract. Inline SVG/MathML also
requires separate review because foreign-content parsing differs from HTML raw
text; none of the 50 current pages uses inline SVG or MathML. External image
references remain supported. CDATA, marked sections
and declarations other than ordinary HTML5 doctypes or comments are rejected
before parsing. This scan is conservative: all
inline script elements are checked, including data script elements. Symlinked
HTML files fail, matching the builder's refusal of symlinks. An empty HTML scope
also fails. Artifact output is already required to reside outside this tree.

Regression tests exercise secondary pages, nested additions, changed script
bodies, source origins, inline event/JavaScript URL attributes and empty scope.
The whole-source check must pass with the same `_headers` bytes after the two
script extractions. These checks prepare the source for a header rollout; only
a separate exact-source live readback can establish provider enforcement.
