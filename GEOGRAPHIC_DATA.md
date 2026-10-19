# Offline geographic aliases

`entity_aliases.py` uses the city and alternate-name data distributed in
`geonamescache==3.0.0`, with the 15,000-population city dataset. It covers all
available countries; no destination is specially added for a mailbox or test.
Arabic normalization and Latin/Arabic aliases are matched locally. No query,
email or entity is sent to a geocoding service.

Data source: [GeoNames](https://www.geonames.org/), licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Packaging/library: [geonamescache](https://github.com/yaph/geonamescache), MIT.

This is an alias lookup, not an authoritative itinerary source. Colliding names
remain unresolved; small towns outside the dataset use literal matching. Airport
codes are not expanded into cities or airports. Answer values, airports, times,
and booking identifiers must still be proved by the same source record.

Updating the dependency changes geographic coverage and requires rerunning entity,
ambiguity, cross-language and tenant-isolation acceptance tests. A data snapshot
may be stale; never infer the current operational status of a destination.
