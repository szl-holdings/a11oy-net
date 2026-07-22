# a11oy.net

Flagship static site for a11oy.net (GitHub Pages behind Cloudflare DNS).

The page is a positioning and navigation surface: every claim links to a governed
repository or public Hugging Face artifact. Its live atlas reads only public Hub
metadata for models, datasets, Spaces, collections, and buckets in the visitor's
browser, resolves each Space's public runtime record with an eight-second timeout,
labels runtime stages without inferring capability health, and remains usable when
an upstream API is unavailable.

No private resources, tokens, model weights, or dataset payloads are requested.

<sub>SLSA: L1 honest · L2 attested · L3 roadmap. Λ = Conjecture 1 (advisory). Trust ceiling 0.97. Labels: MEASURED / REPORTED / MODELED / HEURISTIC / UNKNOWN / UNAVAILABLE. locked-proven = exactly 8 {F1,F4,F7,F11,F12,F18,F19,F22}.</sub>
