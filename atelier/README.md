# Atelier walk (proof origin)

Static forty-model walk on the proof registry.

- This path: https://a11oy.net/atelier/
- Canonical Space: https://huggingface.co/spaces/SZLHOLDINGS/szl-atelier
- Source: https://github.com/szl-holdings/szl-atelier
- Product: https://a-11-oy.com

Nano silhouettes MEASURED in-browser. 1.5B numbers SIGNED, not retrained here. Energy UNAVAILABLE. Λ = Conjecture 1 OPEN.

Doctrine v11. Apache-2.0. SZL Holdings.

## Reader and verification boundary

`/atelier/` is a static proof-origin lab walk. Its JavaScript must parse before the browser can render the catalog, but parse success does not qualify the linked model artifacts or the separate Hugging Face Space.

Run the bounded offline checks from the repository root:

```bash
node --test tests/atelier-script.test.cjs
python -m unittest tests.test_atelier_javascript
```

The checks execute the page script in a network-free Node fixture after removing only the terminal `boot()` call. They cover model-base fallback and HTML escaping; they do not download metadata, load weights, start the canonical Space, or extend any training, energy, performance, safety, or operational claim.
