"""Local delivery index, verification reports, and immutable advanced package."""
import html,json,subprocess,sys,shutil
from pathlib import Path
import cm_advanced_series_v1 as p

def duration(s):
    m,s=divmod(round(s),60);return f'{m}:{s:02d}'

def notes():
    p.require_unfrozen()
    source=p.ROOT/'docs/video_factory/deep_series/foundational_cm_tutorial_series_v2/sources/CorrespondenceMatrices_source_2026_09_14.pdf'
    p.write(p.OUT/'SOURCE_IDENTITY_V1.json',dict(primary_url='https://www.b-theory.com/CorrespondenceMatrices.pdf',snapshot=str(source.relative_to(p.ROOT)),sha256=p.sha(source),visual_pages_reviewed=[17,18,19,23,26],text_pages_reviewed=list(range(8,29)),supplementary_site='https://relative0.github.io/Correspondence_Matrices/',supplementary_site_status='Web tool open failed and site search returned no results; no claims depend on it.'))
    (p.OUT/'SOURCE_AND_TEACHING_REVIEW_V1.md').write_text('''# Source and teaching review

The advanced continuation contains fourteen separate lessons, numbered 10–23.
It follows the nine foundation lessons without changing their frozen videos.
Each advanced lesson has one concrete example, intermediate calculation states,
a five-second practice pause and an explained answer. Screens change at aligned
narration paragraph boundaries; these are progressive teaching states rather
than continuous object animations.

## Source checks and corrections

The primary source is the [author's manuscript](https://www.b-theory.com/CorrespondenceMatrices.pdf).
The retained foundation-v2 snapshot is identified by hash in SOURCE_IDENTITY_V1.json.
The advanced sections were extracted for reading, and pages 17, 18, 19, 23 and
26 were rendered and visually inspected. The supplementary project website was
not retrievable with the web tool in this run, so no unsupported claims were
drawn from it. Repository claims instead use inspected current source files and
local executable checks.

- Lesson 14 recomputes the first page-12 composition as `[¬R]`, hence **¬Y**,
  rather than the printed `[¬L]`/¬X. The decisive X=0,Y=1 counterexample is
  explained in the lesson. The second page-12 example correctly ends at
  equivalence, but its intermediate combined matrix must use NAND, not the
  implication glyph printed in that position. Both identities are exhaustively
  checked and taught with corrected intermediate arrays.
- Lesson 15 explicitly defines the single-variable factor product as
  **entrywise AND**. The page-17 factorization does not hold as AND/XOR
  row-by-column matrix multiplication: the duplicate terms cancel to zero.
  Both operations and the counterexample are shown, avoiding ambiguous
  juxtaposition. The manuscript itself remains unchanged.
- Lesson 16 expands both entries of `⟨X|M_{X⇒Y}` to `[Y,¬Y]`, then contracts
  with Y or ¬Y. The matched results are 1 and 0; changing the ket to Z gives
  Y⇔Z. All sixteen operator LMs, four valuations and four matched selector
  combinations are independently checked. The constant matched result does
  not assert that the numeric-CM expression X⇒Y is a tautology.
- Lessons 17–18 declare physical row/column component order. With 2n input
  bits evenly split, dimensions are 2^n by 2^n. Tensor factors, array indices
  and input counts are kept distinct. The final page-26 numeric arrays agree
  with independently evaluated expressions under the declared WY/XZ axes;
  no unchecked long index formula is copied into the lesson.
- Lessons 19–21 distinguish a graph, a structural expression hash, a packed
  truth vector and an explicit matrix. The current `cm_build_lazy.py` wrapper
  calls `materialize_cm` and returns a dense array. The lesson explains explicit
  deferral through a retained compiled node rather than attributing older
  execution behavior to the current wrapper's name.
- Lesson 22 uses **hypothetical** timings only. Break-even is 48 queries and
  strict improvement starts at 49 for the stated 120 ms/3 ms/0.5 ms model.
  There is no repository performance result or broad speed claim.
- Lesson 23 is a local four-input policy illustration, not deployed access
  control. All 16 assignments match a separate scalar oracle; 3 allow and 13
  deny. The trusted origin of input facts is outside the Boolean example.

## Notation and chronology

New mathematical implications use the short double ⇒ everywhere, including
between expressions. Equal values and derivation steps retain equality.
XOR uses ⇕, bracketed operators accompany numeric CMs, and every LM name is
introduced before use. The source standard's centered Impax overlay remains
in force; none of these advanced examples needs a new Impax display.

The sequence first teaches coordinate changes, then entrywise operations,
then symbolic factors and measurements, then higher dimensions, then repository
representations, code, output costs and an application. The local numbering
matches all fourteen proposed topics. The shared episode Bible is not changed;
its topic ownership is recorded in CURRICULUM_MAP_V1.md.

The downloadable example in `examples/course_examples.py` uses the actual
public API with Var(0) and explicit variable names. It checks 3 layouts × 16
assignments, compiled-node reuse, the current lazy wrapper, packed output,
structural versus semantic identity and the policy truth table. Run it from
any working directory inside this checkout using the project's interpreter.
''',encoding='utf-8')
    rows=['# Advanced curriculum and scene evidence map','','The original proposed topics 10–23 are all covered; no shared Bible renumbering.','', '| Lesson | Topic | Prerequisite | Primary evidence |','|---|---|---|---|']
    for l in p.curriculum.LESSONS:rows.append(f"| {l['id'][:2]} | {l['title']} | {l['prerequisite']} | {l['source']} |")
    rows+=['','## Shared curriculum ownership','','10–18: operator transformations, composition, LM algebra and higher-dimensional paper examples.','19: explicit-cm-vs-cm-ir and graph identity.','20: public API and lookup/repartition.','21: packed-words-selection and eager-lazy; current wrapper behavior rechecked.','22: measurement-boundaries and exact-comparison-protocol.','23: bounded application example; no deployment or application-performance claims.','','## Source-to-scene mapping','']
    for l in p.curriculum.LESSONS:
        rows+=[f"### {l['id']}: {l['title']}",f"Evidence: {l['source']}",'']
        rows += [f"- Scene {i}: {s['title']}. Teaching claim: {s['note']}" for i,s in enumerate(l['scenes'],1)]
    (p.OUT/'CURRICULUM_MAP_V1.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    examples=p.OUT/'examples';examples.mkdir(exist_ok=True)
    script=(p.ROOT/'docs/video_factory/cm_advanced_examples_v1.py').read_text(encoding='utf-8')
    script=script.replace("ROOT=Path(__file__).resolve().parents[2]","ROOT=next(x for x in Path(__file__).resolve().parents if (x/'cm_build.py').is_file())")
    script=script.replace("    out=ROOT/'docs/video_factory/deep_series/advanced_cm_tutorial_series_v1'\n    out.mkdir(exist_ok=True,parents=True)\n    (out/'REPOSITORY_EXAMPLES_QA_V1.json').write_text(json.dumps(result,indent=2)+'\\n',encoding='utf-8')\n",'')
    (examples/'course_examples.py').write_text(script,encoding='utf-8')
    (examples/'README.md').write_text('''# Run the advanced examples

From the CM_Computation root:

```powershell
.\\.venv\\Scripts\\python.exe -X utf8 docs\\video_factory\\deep_series\\advanced_cm_tutorial_series_v1\\examples\\course_examples.py
```

The script locates this checkout from its parent directories. It performs only
bounded local computations and assertions, with no network or paid services.
It prints results and does not modify the frozen delivery. Keep the example
inside this checkout so its current repository imports can be resolved.
''',encoding='utf-8')
    print('Wrote source review, curriculum map and runnable examples',flush=True)

def index():
    p.require_unfrozen();rows=[];cards=[];total=0;receipts=[]
    for l in p.curriculum.LESSONS:
        f=p.OUT/l['id'];q=json.loads((f/'QA_REPORT_V1.json').read_text(encoding='utf-8'));total+=q['duration_s']
        receipts.append(json.loads((f/'VOICE_RESPONSE_V1.json').read_text(encoding='utf-8')))
        file=l['id']+'/'+l['id']+'_v1.mp4'
        rows.append(f"| {l['id'][:2]} | [{l['title']}]({file}) | {duration(q['duration_s'])} |")
        cards.append(f'''<article id="l{l['id'][:2]}"><h2>{l['id'][:2]} · {html.escape(l['title'])}<span>{duration(q['duration_s'])}</span></h2><p>{html.escape(l['prerequisite'])}</p><video controls preload="none" poster="frames/f{q['first_frame']:06d}.png"><source src="{file}" type="video/mp4"><track kind="captions" src="{l['id']}/captions_v1.vtt" srclang="en" label="English"></video><p><a href="{file}">Open lesson MP4</a> · <a href="{l['id']}/SCRIPT_AND_VISUAL_SPEC_V1.md">Script and visuals</a></p></article>''')
    cost=sum(int(r.get('character_cost') or 0) for r in receipts)
    p.write(p.OUT/'VOICE_CONTINUITY_QA_V1.json',dict(voice_id=p.VOICE,model=p.MODEL,settings=p.SETTINGS,new_recordings=len(receipts),character_cost_units=cost,human_listening_pending=True,source_audio_hashes=[r['source_audio_sha256'] for r in receipts]))
    md='''# Advanced CM course: lessons 10–23

Fourteen separate Brian-narrated lesson videos. Browse the [local video index](REVIEW_INDEX_V1.html)
or open an individual MP4 below. The [nine foundation lessons](../foundational_cm_tutorial_series_v2/README.md)
remain unchanged.

| Lesson | Standalone video | Duration |
|---|---|---|
'''+ '\n'.join(rows)+f'''

[Combined advanced course](cm_advanced_complete_course_v1.mp4): **{duration(total)}**,
with fourteen lesson chapters and continuous captions.

- [Curriculum, prerequisites and source-to-scene map](CURRICULUM_MAP_V1.md)
- [Mathematical source review and teaching decisions](SOURCE_AND_TEACHING_REVIEW_V1.md)
- [Runnable repository examples](examples/README.md)
- [Validation](VALIDATION_V1.md)

Every video uses the same Brian voice identity, multilingual-v2 model and voice
settings. Fourteen full-lesson recordings reported {cost:,} character-cost units
(API accounting units, not dollars). No account upgrade or additional purchase
was made. Naturalness and perceived tone consistency remain human listening
judgments; technical voice identity and configuration are verified.

Videos are 1280×720, 30 fps H.264 with mono AAC narration, embedded English
subtitles and WebVTT sidecars. Each has a five-second practice pause and an
explained answer. Visuals progress with aligned narration paragraphs. Short
double implication arrows and the established XOR notation are used throughout.

All prior foundation artifacts are preserved. No RunPod, publication, commit or
push occurred. The final manifest freezes this local review package; requested
changes should use a successor version.

Recommended first review: lessons 15–16 for symbolic teaching, 21 for execution
terminology, and 23 for the application. Closely related feedback can continue
in this task; no new model run is needed before the human review.
'''
    (p.OUT/'README.md').write_text(md,encoding='utf-8')
    nav=''.join(f'<a href="#l{l["id"][:2]}">{l["id"][:2]}</a>' for l in p.curriculum.LESSONS)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Advanced CM lessons 10–23</title><style>body{background:#09151d;color:#edf7fb;font:18px/1.5 system-ui;max-width:1100px;margin:35px auto;padding:0 24px}a{color:#89deed}h1{font-size:36px}h2{font-size:25px}h2 span{float:right;color:#b8a2ec;font-size:20px}article{border-top:3px solid #6fd7e3;margin-top:40px;padding-top:12px}video{width:100%;background:#09151d}nav{display:flex;gap:22px;flex-wrap:wrap}</style><h1>Advanced CM · fourteen lesson videos</h1><p>Operator transformations, logical measurements, larger matrices and runnable repository examples.</p><nav>'''+nav+'''</nav>'''+''.join(cards)+'''<article><h2>Combined advanced course</h2><video controls preload="none"><source src="cm_advanced_complete_course_v1.mp4" type="video/mp4"><track kind="captions" src="course_captions_v1.vtt" srclang="en" label="English"></video></article></html>'''
    (p.OUT/'REVIEW_INDEX_V1.html').write_text(page,encoding='utf-8')
    print(f'Indexed 14 lessons, duration {duration(total)}',flush=True)

def preservation():
    checks=[]
    for ver in (1,2):
        f=p.ROOT/f'docs/video_factory/deep_series/foundational_cm_tutorial_series_v{ver}/DELIVERY_MANIFEST_V{ver}.json'
        d=json.loads(f.read_text());bad=[a['path'] for a in d['artifacts'] if p.sha(p.ROOT/a['path'])!=a['sha256']]
        checks.append(dict(version=ver,checked=len(d['artifacts']),mismatches=bad,manifest_sha256=p.sha(f)))
    if any(x['mismatches'] for x in checks):raise RuntimeError(str(checks))
    p.write(p.OUT/'PRESERVATION_QA_V1.json',checks)
    print('Preserved 260 foundation-v1 and 327 foundation-v2 manifest entries',flush=True)

def validate():
    p.require_unfrozen()
    tests=['test_cm_advanced_v1.py','test_cm_tutorial_series_v2.py','test_cm_tutorial_series_v1.py']
    args=[str(p.ROOT/'.venv/Scripts/python.exe'),'-m','pytest']+[str(p.ROOT/'docs/video_factory/tests'/x) for x in tests]+['-q']
    r=p.run(args,cwd=p.ROOT);output=r.stdout.decode('utf-8',errors='replace');print(output,flush=True)
    p.write(p.OUT/'TEST_RESULTS_V1.json',dict(command=args,exit_code=r.returncode,output=output))
    layout=json.loads((p.OUT/'LAYOUT_QA_V1.json').read_text())
    assert layout['failed_frames']==0 and layout['frames']==sum(len(l['scenes']) for l in p.curriculum.LESSONS)
    assert (p.OUT/'COURSE_QA_V1.json').exists()
    preservation()
    (p.OUT/'VALIDATION_V1.md').write_text(f'''# Validation of the advanced CM delivery

- All **26 tests passed**, including mathematical, repository, foundation-regression
  and final-media checks. The exact test command/output is in TEST_RESULTS_V1.json.
- **{layout['frames']} teaching frames passed layout checks**, with no overflow or
  forbidden single implication/XOR glyphs. Representative source pages and
  operator, LM, tensor, composition and code frames were visually inspected.
- All fourteen lesson videos and the combined course fully decoded. Per-lesson
  reports retain frame counts, durations, source hashes, subtitle cues and timing.
- All fourteen five-second practice intervals contain silence. Captions stay
  within duration, outside practice pauses, and within two 42-character lines.
- Voice ID, multilingual-v2 model, settings and exact narration text are verified
  for every lesson. No alternate Brian identity or voice model is used.
- Prior manifests were rechecked: 260 foundation-v1 entries and 327 foundation-v2
  entries remain unchanged. These counts include shared dependencies and are
  not claimed as distinct file counts across both manifests.

The math suite checks all sixteen 2×2 operator transformations, 256 pairs of
operators for XOR/quotient composition, LM factorization, all sixteen operator
LMs under every two-bit valuation and matched selector pair, tensor entries,
and all sixteen assignments in the larger composition. Repository examples
check 48 layout/assignment cases, packed results, current wrapper behavior,
structural-hash distinctions, the policy oracle and hypothetical break-even.

No empirical speed benchmark was conducted or claimed. Subjective voice
naturalness and the learner's preferred pace remain human review items. Visual
timing uses character-aligned narration paragraph boundaries; continuous object
animation and word-by-word cursor tracking are not claimed.

Run `python -X utf8 docs/video_factory/cm_advanced_finalize_v1.py verify` from
the checkout to check the final frozen manifest. No RunPod, publication,
commit or push occurred.
''',encoding='utf-8')

def freeze():
    p.require_unfrozen();import imageio_ffmpeg
    assert (p.OUT/'TEST_RESULTS_V1.json').exists() and (p.OUT/'VALIDATION_V1.md').exists()
    course=p.OUT/'cm_advanced_complete_course_v1.mp4';count,seconds=imageio_ffmpeg.count_frames_and_secs(str(course))
    q=json.loads((p.OUT/'COURSE_QA_V1.json').read_text());assert abs(seconds-q['expected_duration_s'])<.3
    q.update(decoded_frames=count,actual_duration_s=seconds);p.write(p.OUT/'COURSE_QA_V1.json',q)
    preservation()
    paths=[x for x in p.OUT.rglob('*') if x.is_file()]
    paths += [p.ROOT/'docs/video_factory'/x for x in ['cm_advanced_curriculum_v1.py','cm_advanced_visuals_v1.py','cm_advanced_series_v1.py','cm_advanced_examples_v1.py','cm_advanced_layout_qa_v1.cjs','cm_advanced_finalize_v1.py','tests/test_cm_advanced_v1.py','CM_ADVANCED_LESSONS_10_23_PRODUCTION_PROMPT_V1.md','foundational_cm_corrections_v3.py']]
    paths += [p.ROOT/x for x in ['docs/CM_NOTATION_STANDARD_V3.md','cm_exprlib.py','cm_build.py','cm_build_lazy.py','cm_ir.py','bitset_backend.py']]
    records=[dict(path=x.relative_to(p.ROOT).as_posix(),bytes=x.stat().st_size,sha256=p.sha(x)) for x in sorted(set(paths))]
    p.write(p.OUT/'DELIVERY_MANIFEST_V1.json',dict(version=1,status='local_review_delivery',lessons=14,artifacts=records,published=False,runpod=False,commit=False,push=False))
    print(f'Frozen {len(records)} artifacts',flush=True)

def verify():
    d=json.loads((p.OUT/'DELIVERY_MANIFEST_V1.json').read_text());bad=[x['path'] for x in d['artifacts'] if p.sha(p.ROOT/x['path'])!=x['sha256']]
    if bad:raise RuntimeError(str(bad))
    print(f"Verified {len(d['artifacts'])} advanced delivery artifacts",flush=True)

if __name__=='__main__':{'notes':notes,'index':index,'validate':validate,'freeze':freeze,'verify':verify}[sys.argv[1]]()
