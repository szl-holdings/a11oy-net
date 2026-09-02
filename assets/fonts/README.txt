Self-hosted web fonts for a11oy.net
===================================

These are the display and body faces for this origin's editorial identity.
They are committed here (rather than loaded from a font CDN) so that the
Content-Security-Policy directive `font-src 'self' data:` in /_headers and in
the fallback <meta> CSP stays byte-identical: no third-party font origin is
contacted by this site, and no CSP allowance had to be widened.

Files, all latin-subset WOFF2 taken from the Google Fonts static endpoint
(fonts.gstatic.com) on 2026-09-01:

  fraunces-latin-var.woff2               Fraunces, variable (opsz 9..144, wght 300..700)
                                         upstream: https://fonts.google.com/specimen/Fraunces
  instrument-serif-latin-italic.woff2    Instrument Serif, italic 400
                                         upstream: https://fonts.google.com/specimen/Instrument+Serif
  inter-latin-var.woff2                  Inter, variable (wght 300..700)
                                         upstream: https://fonts.google.com/specimen/Inter

Licence: all three families are published by their authors under the
SIL Open Font License, Version 1.1 (https://openfontlicense.org). The OFL
permits redistribution of the font binaries, including bundling with a web
page, provided the licence notice travels with them; this file is that notice.
Copyright of each face remains with its respective authors:

  Fraunces          Copyright (c) The Fraunces Project Authors
                    https://github.com/undercasetype/Fraunces
  Instrument Serif  Copyright (c) The Instrument Serif Project Authors
                    https://github.com/Instrument/instrument-serif
  Inter             Copyright (c) The Inter Project Authors
                    https://github.com/rsms/inter

No font file has been modified, renamed inside its own name table, or
re-licensed. Each @font-face rule in /index.html declares the same
unicode-range that the upstream latin subset carries, so a glyph outside that
range falls back to the local serif/sans stack rather than silently changing
metrics.
