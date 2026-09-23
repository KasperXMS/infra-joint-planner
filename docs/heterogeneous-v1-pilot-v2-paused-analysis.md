# Heterogeneous v1 paused-pilot audit

Schedule factorization valid: `True`; valid completed: `75/108`; pending: `33`; scheduled-ID invalid: `0`.

The queue was paused after the active atomic run completed. The next scheduled run has no result, trace, metadata, or run directory. A28 and RTX qdiscs were independently verified restored to `mq` and `noqueue`, and all four Workers were available with `in_flight=0`.

## Coverage

| Mbps | Size | Placement | n | Median E2E ms | E2E values ms | Median transfer ms | Transfer values ms | Transfer bytes | Validity |
|---:|:---:|:---|---:|---:|:---|---:|:---|:---|:---|
| 3 | S | forced-a28 | 2 | 178197.351 | [179149.846, 177244.856] | 0.0 | [0.0, 0.0] | [0, 0] | all_completed_valid |
| 3 | S | forced-rtx | 2 | 75843.411 | [76098.579, 75588.244] | 23735.411 | [23805.141, 23665.68] | [8406731, 8406731] | all_completed_valid |
| 3 | M | forced-a28 | 1 | 185611.553 | [185611.553] | 0.0 | [0.0] | [0] | all_completed_valid |
| 3 | M | forced-rtx | 2 | 149883.441 | [149525.243, 150241.639] | 94036.756 | [94014.824, 94058.689] | [33621241, 33621241] | all_completed_valid |
| 3 | L | forced-a28 | 2 | 203203.665 | [201948.09, 204459.241] | 0.0 | [0.0, 0.0] | [0, 0] | all_completed_valid |
| 3 | L | forced-rtx | 3 | 447718.389 | [449700.038, 447113.123, 447718.389] | 375619.379 | [375619.379, 375622.778, 375605.165] | [134499446, 134499446, 134499446] | all_completed_valid |
| 10 | S | forced-a28 | 2 | 178758.267 | [172491.448, 185025.086] | 0.0 | [0.0, 0.0] | [0, 0] | all_completed_valid |
| 10 | S | forced-rtx | 2 | 58944.613 | [59300.746, 58588.481] | 7199.645 | [7173.331, 7225.96] | [8406731, 8406731] | all_completed_valid |
| 10 | M | forced-a28 | 2 | 184945.165 | [184554.058, 185336.272] | 0.0 | [0.0, 0.0] | [0, 0] | all_completed_valid |
| 10 | M | forced-rtx | 2 | 84504.872 | [84602.673, 84407.071] | 28510.389 | [28403.405, 28617.372] | [33621241, 33621241] | all_completed_valid |
| 10 | L | forced-a28 | 3 | 197718.993 | [194875.765, 197718.993, 204736.287] | 0.0 | [0.0, 0.0, 0.0] | [0, 0, 0] | all_completed_valid |
| 10 | L | forced-rtx | 3 | 184753.789 | [184753.789, 186406.052, 183120.076] | 113311.093 | [113311.093, 114164.256, 113069.977] | [134499446, 134499446, 134499446] | all_completed_valid |
| 30 | S | forced-a28 | 2 | 181179.394 | [180291.203, 182067.584] | 0.0 | [0.0, 0.0] | [0, 0] | all_completed_valid |
| 30 | S | forced-rtx | 3 | 55522.086 | [55522.086, 56119.554, 54379.938] | 2660.388 | [2504.708, 2660.388, 3061.34] | [8406731, 8406731, 8406731] | all_completed_valid |
| 30 | M | forced-a28 | 3 | 176963.754 | [176963.754, 174151.948, 188964.314] | 0.0 | [0.0, 0.0, 0.0] | [0, 0, 0] | all_completed_valid |
| 30 | M | forced-rtx | 2 | 66926.318 | [66465.16, 67387.475] | 9999.448 | [10276.172, 9722.724] | [33621241, 33621241] | all_completed_valid |
| 30 | L | forced-a28 | 2 | 198992.162 | [202672.614, 195311.71] | 0.0 | [0.0, 0.0] | [0, 0] | all_completed_valid |
| 30 | L | forced-rtx | 2 | 110298.03 | [109893.291, 110702.769] | 38280.665 | [38281.007, 38280.323] | [134499446, 134499446] | all_completed_valid |
| 100 | S | forced-a28 | 3 | 174946.503 | [171474.984, 174946.503, 176357.991] | 0.0 | [0.0, 0.0, 0.0] | [0, 0, 0] | all_completed_valid |
| 100 | S | forced-rtx | 2 | 53203.267 | [52538.378, 53868.156] | 1396.556 | [1278.797, 1514.316] | [8406731, 8406731] | all_completed_valid |
| 100 | M | forced-a28 | 3 | 181271.24 | [181741.426, 181271.24, 178451.632] | 0.0 | [0.0, 0.0, 0.0] | [0, 0, 0] | all_completed_valid |
| 100 | M | forced-rtx | 1 | 60704.601 | [60704.601] | 4105.355 | [4105.355] | [33621241] | all_completed_valid |
| 100 | L | forced-a28 | 1 | 191002.299 | [191002.299] | 0.0 | [0.0] | [0] | all_completed_valid |
| 100 | L | forced-rtx | 1 | 85130.041 | [85130.041] | 13389.638 | [13389.638] | [134499446] | all_completed_valid |
| 300 | S | forced-a28 | 3 | 176347.743 | [176347.743, 175315.138, 178764.791] | 0.0 | [0.0, 0.0, 0.0] | [0, 0, 0] | all_completed_valid |
| 300 | S | forced-rtx | 1 | 53678.561 | [53678.561] | 2175.195 | [2175.195] | [8406731] | all_completed_valid |
| 300 | M | forced-a28 | 3 | 180859.191 | [179476.831, 180859.191, 183989.35] | 0.0 | [0.0, 0.0, 0.0] | [0, 0, 0] | all_completed_valid |
| 300 | M | forced-rtx | 2 | 59656.224 | [59713.373, 59599.076] | 3961.921 | [3463.988, 4459.855] | [33621241, 33621241] | all_completed_valid |
| 300 | L | forced-a28 | 1 | 199654.591 | [199654.591] | 0.0 | [0.0] | [0] | all_completed_valid |
| 300 | L | forced-rtx | 2 | 94426.145 | [89598.051, 99254.239] | 15308.794 | [18488.791, 12128.797] | [134499446, 134499446] | all_completed_valid |
| 1000 | S | forced-a28 | 2 | 177123.803 | [178035.234, 176212.372] | 0.0 | [0.0, 0.0] | [0, 0] | all_completed_valid |
| 1000 | S | forced-rtx | 1 | 53920.262 | [53920.262] | 1514.595 | [1514.595] | [8406731] | all_completed_valid |
| 1000 | M | forced-a28 | 3 | 179904.375 | [179320.695, 208765.518, 179904.375] | 0.0 | [0.0, 0.0, 0.0] | [0, 0, 0] | all_completed_valid |
| 1000 | M | forced-rtx | 2 | 59098.553 | [59204.507, 58992.598] | 3361.286 | [3289.816, 3432.757] | [33621241, 33621241] | all_completed_valid |
| 1000 | L | forced-a28 | 2 | 199066.206 | [201018.844, 197113.568] | 0.0 | [0.0, 0.0] | [0, 0] | all_completed_valid |
| 1000 | L | forced-rtx | 2 | 81461.056 | [83839.181, 79082.931] | 9686.676 | [10881.477, 8491.875] | [134499446, 134499446] | all_completed_valid |

## Placement preference

### S

| Mbps | n A28/RTX | median A28 ms | median RTX ms | RTX - A28 ms | Preferred |
|---:|:---:|---:|---:|---:|:---|
| 3 | 2/2 | 178197.351 | 75843.411 | -102353.94 | strong-4090 |
| 10 | 2/2 | 178758.267 | 58944.613 | -119813.654 | strong-4090 |
| 30 | 2/3 | 181179.394 | 55522.086 | -125657.308 | strong-4090 |
| 100 | 3/2 | 174946.503 | 53203.267 | -121743.236 | strong-4090 |
| 300 | 3/1 | 176347.743 | 53678.561 | -122669.182 | strong-4090 |
| 1000 | 2/1 | 177123.803 | 53920.262 | -123203.541 | strong-4090 |

### M

| Mbps | n A28/RTX | median A28 ms | median RTX ms | RTX - A28 ms | Preferred |
|---:|:---:|---:|---:|---:|:---|
| 3 | 1/2 | 185611.553 | 149883.441 | -35728.112 | strong-4090 |
| 10 | 2/2 | 184945.165 | 84504.872 | -100440.293 | strong-4090 |
| 30 | 3/2 | 176963.754 | 66926.318 | -110037.436 | strong-4090 |
| 100 | 3/1 | 181271.24 | 60704.601 | -120566.639 | strong-4090 |
| 300 | 3/2 | 180859.191 | 59656.224 | -121202.967 | strong-4090 |
| 1000 | 3/2 | 179904.375 | 59098.553 | -120805.822 | strong-4090 |

### L

| Mbps | n A28/RTX | median A28 ms | median RTX ms | RTX - A28 ms | Preferred |
|---:|:---:|---:|---:|---:|:---|
| 3 | 2/3 | 203203.665 | 447718.389 | 244514.724 | A28 |
| 10 | 3/3 | 197718.993 | 184753.789 | -12965.204 | strong-4090 |
| 30 | 2/2 | 198992.162 | 110298.03 | -88694.132 | strong-4090 |
| 100 | 1/1 | 191002.299 | 85130.041 | -105872.258 | strong-4090 |
| 300 | 1/2 | 199654.591 | 94426.145 | -105228.446 | strong-4090 |
| 1000 | 2/2 | 199066.206 | 81461.056 | -117605.15 | strong-4090 |

## Observed crossover brackets

- S: no in-range sign change; RTX is already preferred at 3 Mbps and remains preferred at every observed higher point.
- M: no in-range sign change; RTX is already preferred at 3 Mbps and remains preferred at every observed higher point.
- L: 3--10 Mbps (delta RTX-A28 244514.724 -> -12965.204 ms).

## Within-cell variation (n >= 2)

| Mbps | Size | Placement | n | mean ms | sample std ms | CV % | range ms | relative range % |
|---:|:---:|:---|---:|---:|---:|---:|---:|---:|
| 3 | S | forced-a28 | 2 | 178197.351 | 1347.032 | 0.756 | 1904.991 | 1.069 |
| 3 | S | forced-rtx | 2 | 75843.411 | 360.861 | 0.476 | 510.335 | 0.673 |
| 3 | M | forced-rtx | 2 | 149883.441 | 506.568 | 0.338 | 716.396 | 0.478 |
| 3 | L | forced-a28 | 2 | 203203.665 | 1775.652 | 0.874 | 2511.151 | 1.236 |
| 3 | L | forced-rtx | 3 | 448177.183 | 1353.108 | 0.302 | 2586.915 | 0.578 |
| 10 | S | forced-a28 | 2 | 178758.267 | 8862.62 | 4.958 | 12533.638 | 7.012 |
| 10 | S | forced-rtx | 2 | 58944.613 | 503.647 | 0.854 | 712.265 | 1.208 |
| 10 | M | forced-a28 | 2 | 184945.165 | 553.108 | 0.299 | 782.214 | 0.423 |
| 10 | M | forced-rtx | 2 | 84504.872 | 138.312 | 0.164 | 195.602 | 0.231 |
| 10 | L | forced-a28 | 3 | 199110.349 | 5075.37 | 2.549 | 9860.522 | 4.987 |
| 10 | L | forced-rtx | 3 | 184759.972 | 1642.996 | 0.889 | 3285.975 | 1.779 |
| 30 | S | forced-a28 | 2 | 181179.394 | 1256.091 | 0.693 | 1776.38 | 0.98 |
| 30 | S | forced-rtx | 3 | 55340.526 | 883.906 | 1.597 | 1739.616 | 3.133 |
| 30 | M | forced-a28 | 3 | 180026.672 | 7866.87 | 4.37 | 14812.366 | 8.37 |
| 30 | M | forced-rtx | 2 | 66926.318 | 652.175 | 0.974 | 922.315 | 1.378 |
| 30 | L | forced-a28 | 2 | 198992.162 | 5204.945 | 2.616 | 7360.904 | 3.699 |
| 30 | L | forced-rtx | 2 | 110298.03 | 572.388 | 0.519 | 809.478 | 0.734 |
| 100 | S | forced-a28 | 3 | 174259.826 | 2512.883 | 1.442 | 4883.007 | 2.791 |
| 100 | S | forced-rtx | 2 | 53203.267 | 940.295 | 1.767 | 1329.778 | 2.499 |
| 100 | M | forced-a28 | 3 | 180488.099 | 1779.232 | 0.986 | 3289.794 | 1.815 |
| 300 | S | forced-a28 | 3 | 176809.224 | 1770.523 | 1.001 | 3449.653 | 1.956 |
| 300 | M | forced-a28 | 3 | 181441.791 | 2311.985 | 1.274 | 4512.519 | 2.495 |
| 300 | M | forced-rtx | 2 | 59656.224 | 80.82 | 0.135 | 114.297 | 0.192 |
| 300 | L | forced-rtx | 2 | 94426.145 | 6827.956 | 7.231 | 9656.187 | 10.226 |
| 1000 | S | forced-a28 | 2 | 177123.803 | 1288.958 | 0.728 | 1822.862 | 1.029 |
| 1000 | M | forced-a28 | 3 | 189330.196 | 16834.012 | 8.891 | 29444.823 | 16.367 |
| 1000 | M | forced-rtx | 2 | 59098.553 | 149.843 | 0.254 | 211.909 | 0.359 |
| 1000 | L | forced-a28 | 2 | 199066.206 | 2761.447 | 1.387 | 3905.277 | 1.962 |
| 1000 | L | forced-rtx | 2 | 81461.056 | 3363.176 | 4.129 | 4756.249 | 5.839 |

## Queue reduction recommendation

Minimum required remaining runs: `1`.

Candidate regimes from current evidence: `{'H_low': 3.0, 'H_mid': 10.0, 'H_high': 30.0}`.

Required run IDs:

- `hetero-v1-pilot-bw3-l-forced-a28-r02-v2-audit1`

Optional n=3 confirmation at H_high (not part of the minimum):

- `hetero-v1-pilot-bw30-l-forced-a28-r02-v2-audit1`
- `hetero-v1-pilot-bw30-l-forced-rtx-r03-v2-audit1`

Remaining pending runs marked unnecessary for this preliminary stage: `32`.

S and M already prefer RTX at the minimum tested bandwidth and at every higher observed point, so no remaining run in the fixed 3--1000 Mbps schedule can create an in-range sign-change bracket unless a current sign reverses. L has an observed 3--10 Mbps bracket; 30 Mbps is the first clearly remote-favoring point above it.

All pending run IDs not required by the minimum:

- `hetero-v1-pilot-bw30-s-forced-a28-r02-v2-audit1`
- `hetero-v1-pilot-bw10-s-forced-rtx-r01-v2-audit1`
- `hetero-v1-pilot-bw30-l-forced-a28-r02-v2-audit1`
- `hetero-v1-pilot-bw10-m-forced-a28-r03-v2-audit1`
- `hetero-v1-pilot-bw100-l-forced-rtx-r01-v2-audit1`
- `hetero-v1-pilot-bw1000-l-forced-a28-r02-v2-audit1`
- `hetero-v1-pilot-bw1000-s-forced-rtx-r03-v2-audit1`
- `hetero-v1-pilot-bw100-l-forced-a28-r03-v2-audit1`
- `hetero-v1-pilot-bw10-s-forced-a28-r02-v2-audit1`
- `hetero-v1-pilot-bw10-m-forced-rtx-r01-v2-audit1`
- `hetero-v1-pilot-bw300-s-forced-rtx-r02-v2-audit1`
- `hetero-v1-pilot-bw1000-m-forced-rtx-r02-v2-audit1`
- `hetero-v1-pilot-bw3-m-forced-a28-r02-v2-audit1`
- `hetero-v1-pilot-bw30-l-forced-rtx-r03-v2-audit1`
- `hetero-v1-pilot-bw300-l-forced-a28-r02-v2-audit1`
- `hetero-v1-pilot-bw100-s-forced-rtx-r02-v2-audit1`
- `hetero-v1-pilot-bw300-s-forced-rtx-r03-v2-audit1`
- `hetero-v1-pilot-bw300-l-forced-rtx-r01-v2-audit1`
- `hetero-v1-pilot-bw3-m-forced-a28-r03-v2-audit1`
- `hetero-v1-pilot-bw3-s-forced-rtx-r02-v2-audit1`
- `hetero-v1-pilot-bw100-l-forced-a28-r01-v2-audit1`
- `hetero-v1-pilot-bw1000-l-forced-rtx-r01-v2-audit1`
- `hetero-v1-pilot-bw300-m-forced-rtx-r02-v2-audit1`
- `hetero-v1-pilot-bw100-l-forced-rtx-r02-v2-audit1`
- `hetero-v1-pilot-bw3-m-forced-rtx-r01-v2-audit1`
- `hetero-v1-pilot-bw100-m-forced-rtx-r03-v2-audit1`
- `hetero-v1-pilot-bw3-s-forced-a28-r01-v2-audit1`
- `hetero-v1-pilot-bw100-m-forced-rtx-r02-v2-audit1`
- `hetero-v1-pilot-bw30-m-forced-rtx-r02-v2-audit1`
- `hetero-v1-pilot-bw1000-s-forced-rtx-r01-v2-audit1`
- `hetero-v1-pilot-bw300-l-forced-a28-r03-v2-audit1`
- `hetero-v1-pilot-bw1000-s-forced-a28-r03-v2-audit1`
