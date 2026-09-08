# Narration and mux plan — foundational CM production v2

Status: offline neural pipeline implemented; human voice selection pending

## Voice candidates

Three 20–22 second readings use identical text and speed:

- `af_heart` — provisional default;
- `af_bella`;
- `bf_emma`.

All are generated locally with Kokoro ONNX. No text, audio, or credential is
sent to a voice service. Windows SAPI remains scratch-only and is not accepted
for a master.

## Spoken/display separation

The scripts write spoken forms such as “C M,” “L M,” “V sub T,” “ket one,”
and “bra one.” The screen and WebVTT captions retain compact mathematical
notation. The speech engine is never asked to pronounce raw Unicode formulas.

Retrieval scenes are represented as speech, a real four-second silent segment,
then the answer. Cue audio must fit its declared scene window without exceeding
1.12× synthesis speed.

## Audio and mux contract

- Offline neural narration, 24 kHz model output.
- Normalized narration master: 48 kHz mono PCM, target −18 LUFS and −1.5 dBTP.
- Episode master: existing H.264 visual stream copied without re-encoding,
  mono AAC narration at 160 kbit/s, and embedded English `mov_text` captions.
- Sidecar WebVTT remains beside the master.
- Full decode check is mandatory after mux.
- Final voice choice and final human audio review remain release gates.
- Publication, commit, and push remain unauthorized.
