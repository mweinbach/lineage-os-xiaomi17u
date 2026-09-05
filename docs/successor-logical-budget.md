# Successor logical image budget

The stock Package7 evidence remains the source of every physical GPT bound and
the original logical-image sizes in `image_budgets`. The successor build
`nezha.a6d3109ae93158c498bb30b0` produced a 778,199,040-byte `system_ext.img`
after the factory camera integration. Its admitted image identity is
`c75d16fa4d06d2d30089cf469df9d845410cbd66446d4018cbec667c24521cc4`.

The maintained AVB profile therefore carries one explicit logical override for
`system_ext`, from the 713,158,656-byte stock baseline to that exact measured
size. The override pins the admission record identity and build number. It does
not alter a physical GPT partition, the TWRP working76 identity, or the
`qti_dynamic_partitions_a` maximum of 15,290,335,232 bytes.

The eight admitted logical images total 9,476,509,696 bytes, leaving
5,813,825,536 bytes within the unchanged group maximum. Verification still
checks every image against its individual bound and checks the sum of all
present logical images against the group maximum. Adding another override,
changing the measured size, or changing its provenance is rejected by the
reviewed profile loader.
