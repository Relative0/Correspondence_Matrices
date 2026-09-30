# Counterexamples and qualifications

No T3 correctness counterexample was found. The independent Theory replay reproduces the named-coordinate histogram witness xy versus (1-x)y, the parity reset-horizon failure and the one-bit class-identity warning. Those counterexamples concern different state/operational claims, not the frozen cumulative T3 construction.

## Small finite-size payload/byte witness

With nonempty cut p=q=2, r=1, k=0, the dense mathematical payload is 7 bits and the raw factor payload is 8 bits. Both implemented artifacts serialize to 61 bytes. Thus the strict mathematical inequality does not guarantee a strict serialized-byte win. This is the smallest total dimension for such a dense favorable payload with nonempty blocks (for n<4 even k=0 is not favorable, and higher k only increases the moment term). The `rectangle_m2` row in `results/DENSE_MATCHED_BYTE_EXCEPTIONS.json` supplies an executed witness.

`minimize_metadata.py` reproduces the bounded minimization and emits lexicographically least nonzero single-profile factors, the exact two binary files and `MINIMIZED_MATCHED_BYTE_WITNESS.json`. The explicit search order/range is recorded; no unbounded lexicographic minimality beyond that scope is claimed.

The separately instantiated p=1,q=3,r=1,k=0 example in `METADATA_WITNESS.json` has seven dense bits versus ten raw factor bits, but a 61-byte complete state. It refutes interpreting the seven-bit payload as complete serialization, while its 62-byte raw serialization is still larger. These two comparisons must not be confused.

Nine of the 32 primary-favorable realized dense case/depth pairs fail the matched serialized-byte crossover. For example, the natural controller case p=4,q=3,r=3,k=0 predicts 70<72 payload bits but serializes to 81 versus 75 bytes. The frozen criterion was not retrospectively replaced or adjusted. These observations require a metadata-aware finite-size qualification; they do not contradict T3's exact recurrence or its asymptotic bound with metadata.

`results/DENSE_BYTE_EXCEPTIONS.json` compares complete T3 bytes against ideal raw payload; `results/DENSE_MATCHED_BYTE_EXCEPTIONS.json` compares two complete serializers. The primitive sparse label term and metadata/padding remain explicit in `STORAGE.json` and `LIFECYCLE_SUMMARY.csv`.
