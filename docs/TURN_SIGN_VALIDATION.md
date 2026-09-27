# Turn-sign candidate evaluation — 17 September 2026

Candidate: star092304/traffic-sign-detection-vietnam-yolo, pinned revision 58719e5c03bf5fa2817b59f9c7c3c385d3e92c9d. The actual checkpoint contains the missing explicit turn-prohibition labels. Its upstream dataset scores are not project accuracy measurements.

## Independent source samples

- Indian no-left-turn illustration, by Sugeesh, released to the public domain: https://commons.wikimedia.org/wiki/File:Road_Sign_No_Left_Turn.jpg . Visual inspection establishes this is a diagram, not a photograph. Stored unchanged as temp/qa/turn_signs/Road_Sign_No_Left_Turn.jpg.
- Barcelona street photograph showing a no-left-turn sign beside a red signal, by Eric Fischer: https://commons.wikimedia.org/wiki/File:No_left_turn_sign_with_stoplight_(17821040904).jpg . Original downloaded unchanged to temp/qa/turn_signs. Source page provides attribution and reuse terms.

## Actual GPU results

The normal 640-pixel detector missed the target sign in both inputs. In the Barcelona photograph it detected an unrelated no-stopping/no-parking sign; no turn constraint was accepted. See positive_results.json in the sample directory. This is one real positive photograph plus one positive illustration, not a multi-class benchmark.

A diagnostic crop experiment used existing IVP colour/shape proposals with neutral padding and a lower raw reporting threshold of 0.1. This did not modify production thresholds. It misclassified the Indian illustration as No left turn for cars at 0.677. The IVP proposal stage also missed the dark, oblique main sign in the Barcelona photograph, showing a separate localisation limitation. See crop_diagnostic.json.

Earlier four-image negative smoke results in temp/qa/turn_sign_smoke.json contain no accepted turn constraints but include raw false labels on a street photograph and no-vehicles crop.

## Decision

Localisation follow-up: the photographed sign's shaded border includes HSV hue values between 161 and 168. The old upper red interval (>168) retained only its lower portion, failing aspect ratio. Extending the sign-only interval to >160 recovers a candidate box [242,475,630,840] covering the sign, with existing size/shape filters unchanged. Eight focused sign tests pass, including dark-red acceptance and purple rejection. The full-image bus negative remains cannot_assess (top classifier score 0.0795). A shape-only negative assertion on the bus failed; the actual classifier/shape combination, not colour shape alone, rejects that input. Results: localisation_fix.json.

Neither classifier correctly interprets the recovered sign: GTSRB returns a low-confidence unsupported class, and the candidate Vietnamese detector calls the crop Speed limit 70km/h at 0.781. Both remain cannot_assess. A padded crop gives no detections. Results: localised_turn_results.json. The localisation fix is applied, but does not solve missing turn-sign recognition.

Do not connect this checkpoint to automatic violation decisions based on these results. Keep the diagnostic adapter and reproducible records for comparison. Its label coverage is useful, but transfer performance on these inputs is inadequate. Next work must evaluate another checkpoint or prepare representative labelled turn-sign data; lowering acceptance thresholds does not resolve wrong-class predictions. No-left/no-right/no-U-turn recognition, sign applicability, and automatic turn interpretation remain unfinished.


## Replacement classifier evaluation - 24 September 2026

Screened six repository metadata records, saved as temp/qa/turn_signs/replacement_metadata.json. Phearith/Traffic_Sign_Detection_Using_YOLOv8 references Mapillary in its bibliography but its actual data.yaml lists 33 GTSRB-style classes, without the required explicit turn prohibitions; a reference alone is not label coverage.

Tested dima806/traffic_sign_detection, revision 3d8191d18c7d5ba982b19971c9f84f597b0a7aa7, using its supplied image processor and safetensors on CUDA. SHA256: df8b0859a0a1550cca9e2cbdae315120e36a597f9077890685651c9d9bc2476a. The root checkpoint includes Dont Go Left, Dont Go Right and No Uturn labels. It nevertheless predicts Dont Go straight or left at only 0.0621 on the Indian illustration and 0.0395 on the automatically recovered Barcelona sign crop. These do not establish correct recognition. Full photographs and automatic colour/shape candidate crops were also recorded, including Indian rider-image negatives.

Results: temp/qa/turn_signs/replacement_vit_results.json. Reproduction: temp/evaluate_turn_vit_local.py; weights stored separately under H:/CodexStorage/ivp-ai/models/turn-sign-vit-3d8191d. The low scores and wrong top labels are observed failures, not evidence of their cause. Do not adopt the model card's upstream accuracy claim or connect this checkpoint to automatic decisions. Training provenance, intermediate checkpoints, or representative labelled data require further investigation.

## Integrated candidate detector - 24 September 2026

The follow-up checkpoint audit found the default dima806 weights identical to checkpoint-1302 (the checkpoint with the best reported evaluation accuracy), so redownloading that checkpoint would not change the result. Fingerprints are saved in temp/qa/turn_signs/checkpoint_fingerprints.json.

Tested yahyagul/traffic-sign-yolov8 at revision 15be2681d3b6e666f45c744219aab84e97a2f1b4. Its 22,545,002-byte best_roboflow.pt SHA256 is 93793cc99ffda2a10e09860e3a7c6383f7c25d470dd604c4555b5b07253a6e2b. The actual checkpoint labels include do_not_turn_l, do_not_turn_r and do_not_u_turn. At imgsz=960, it correctly detects the no-left-turn sign in the full Barcelona photo with score 0.8975 and box [273.67,502.97,603.59,809.46]. It produces no detections on the Indian rider negative. It fails the Indian illustration and tight sign crop. This is only a small development evaluation, not evidence of general Indian sign accuracy or validated right/U-turn recognition. Raw results: temp/qa/turn_signs/yahyagul_results.json.

Replaced the failed default in traffic_ai/turn_signs.py and integrated its observations into Analyzer's scene-sign evidence and model manifest. The adapter checks the pinned checksum, requires an explicit supported class, score >=0.8, a >=24-pixel crop and red circular shape support. Its traffic-light outputs cannot create turn constraints or bypass the existing signal pipeline. Existing approach association and calibrated-turn requirements still apply; recognising a sign alone cannot produce a turn violation.

Actual full-worker run: runs/20260924-122403-0015bf8b. Exported report contains one accepted left-prohibition candidate, no associated approach and no violation events; both output PNGs reopen. Assertions saved as turn_sign_verification.json. This run proves integration and one positive recognition, not completion of automatic prohibited-turn assessment. Next validation requires independent no-right/no-U-turn photographs, Indian signage, negative signs and real turn trajectories with reliable road-plane interpretation.
