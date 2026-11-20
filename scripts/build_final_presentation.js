// Build the DSC 261 final project presentation from verified saved metrics.
const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');

const root = path.resolve(__dirname, '..');
const metrics = JSON.parse(fs.readFileSync(path.join(root, 'artifacts/final-delivery/analysis/metrics.json')));
const integratedPath = path.join(root, 'artifacts/final-delivery/postmerge-track-b/integrated-38-analysis/metrics.json');
const integrated = fs.existsSync(integratedPath) ? JSON.parse(fs.readFileSync(integratedPath)) : null;
const output = path.join(root, 'presentation/CausalBridge-final.pptx');
fs.mkdirSync(path.dirname(output), { recursive: true });

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'CausalBridge project team';
pptx.subject = 'DSC 261 final project evidence';
pptx.title = 'CausalBridge: evidence and causal reasoning';
pptx.lang = 'en-US';

const C = { navy: '142938', ink: '20303A', paper: 'F7F8F5', teal: '237C69', red: 'BB5145', gray: 'A2A8AD', line: 'DCE3E2', white: 'FFFFFF', pale: 'E7F1ED' };
function rect(slide, x, y, w, h, fill, radius=0) {
  slide.addShape(radius ? pptx.ShapeType.roundRect : pptx.ShapeType.rect,
    { x, y, w, h, rectRadius: radius, line: { color: fill, transparency: 100 }, fill: { color: fill }, radius });
}
function txt(slide, text, x, y, w, h, size=22, color=C.ink, bold=false, extra={}) {
  slide.addText(String(text), { x, y, w, h, fontFace: 'Aptos', fontSize: size, color, bold,
    margin: 0, breakLine: false, isTextBox: true, valign: 'mid', ...extra });
}
function base(title, number, dark=false) {
  const s = pptx.addSlide();
  s.background = { color: dark ? C.navy : C.paper };
  txt(s, title, 0.65, 0.43, 11.9, 0.65, 30, dark ? C.white : C.navy, true);
  rect(s, 0.65, 1.2, 12.0, 0.025, dark ? '56717C' : C.line);
  txt(s, `CAUSALBRIDGE  /  DSC 261`, 0.65, 7.08, 5.5, 0.22, 10, dark ? 'AEC0C5' : '667C83');
  txt(s, `${number}`, 12.1, 7.08, 0.5, 0.22, 10, dark ? 'AEC0C5' : '667C83', false, { align: 'right' });
  return s;
}
function line(slide, title, body, y, accent=C.teal) {
  rect(slide, 0.7, y, 0.08, 0.8, accent);
  txt(slide, title, 1.05, y, 3.0, 0.34, 19, C.navy, true);
  txt(slide, body, 4.1, y-0.02, 8.4, 0.87, 17, C.ink);
}
function note(s, t) { s.addNotes(t); }

let s = base('Can evidence make causal answers reliable?', 1, true);
txt(s, 'Structured diagnostics improved the audit trail.\nThey did not establish better causal direction.',
  0.75, 2.05, 11.7, 1.6, 34, C.white, true);
txt(s, 'Two tracks  ·  One local Qwen3 model  ·  Saved requests and raw responses',
  0.78, 5.12, 11.2, 0.48, 20, 'BFD7D1');
note(s, 'Conclusion is bounded to the tested synthetic benchmark and exploratory real pilot.');

s = base('Why direction is difficult', 2);
txt(s, 'A graph can identify a path without identifying its sign.', 0.75, 1.53, 11.5, 0.57, 25, C.ink, true);
rect(s, 0.75, 2.35, 5.7, 2.5, C.pale, 0.12);
rect(s, 6.85, 2.35, 5.7, 2.5, 'F8EBE8', 0.12);
txt(s, 'Model M+', 1.03, 2.66, 5.0, 0.45, 22, C.teal, true);
txt(s, 'P(X,Y) = ¼ in each cell\nEffect of X on Y = +0.30', 1.03, 3.25, 4.9, 1.1, 22);
txt(s, 'Model M−', 7.13, 2.66, 5.0, 0.45, 22, C.red, true);
txt(s, 'P(X,Y) = ¼ in each cell\nEffect of X on Y = −0.30', 7.13, 3.25, 4.9, 1.1, 22);
txt(s, 'The observational evidence is identical. The intervention answers differ.',
  0.75, 5.38, 11.9, 0.7, 21, C.navy, true);
note(s, 'Exact witness and numerical confirmation: docs/track_a_pilot.md and tests/test_pilot_numerical_confirmation.py.');

s = base('What CausalBridge checks', 3);
line(s, 'Track A', 'Question → model parser and planner → graph/numeric tool → verdict checker', 1.72);
line(s, 'Track B', 'E1–E4 evidence package → model direction → typed citation checker → release', 3.02);
line(s, 'ANM', 'Bidirectional residual-dependence diagnostic; score difference is not causal proof', 4.32, C.red);
txt(s, 'Ground truth is exact for the synthetic witness. Real arrows are benchmark references.',
  0.75, 5.84, 11.7, 0.57, 19, C.navy, true);
note(s, 'The checker binds identities, rows, summaries and method outputs; arbitrary prose remains outside its scope.');

s = base('Evaluation contract', 4);
line(s, 'Known graph', '50 questions in 10 synthetic graph groups; 29 answerable, 21 unanswerable', 1.68);
line(s, 'Real pilot', '17 CauseEffectPairs in 7 source groups; 136 live generations', 2.92);
line(s, 'Conditions', 'E1 names, E2 data, E3 names + data, E4 adds ANM; S0/S1 prompts', 4.16);
line(s, 'Derived', 'S2 checker, simple gate and ANM-only reuse saved outputs', 5.4, C.gray);
note(s, 'Track B model: qwen3:8b digest 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41.');

const a = metrics.track_a;
s = base('Track A: synthetic live model pilot', 5);
const aRows = [
  ['Correct answer', a.counts.correct_answer, C.teal],
  ['Wrong answer', a.counts.wrong_answer, C.red],
  ['Correct abstention', a.counts.correct_abstention, C.gray],
  ['False abstention', a.counts.false_abstention, 'D6AA5D'],
];
aRows.forEach(([label, value, color], i) => {
  const y = 1.62 + i * 1.0;
  txt(s, label, 0.75, y, 3.2, 0.38, 19);
  rect(s, 4.0, y, 7.4 * value / 50, 0.48, color);
  txt(s, `${value} / 50`, 11.52, y, 1.0, 0.48, 18, C.ink, true);
});
txt(s, `${a.actual_model_calls} live model stages across 50 cases; one frozen configuration`,
  0.75, 6.2, 11.5, 0.4, 18, C.navy, true);
note(s, 'Source: runs/final-track-a-live-20261119.jsonl and artifacts/final-delivery/analysis/track-a-case-results.json. Each graph group contributes five dependent cases.');

s = base('Track B: the E4 diagnostic dominated', 6);
rect(s, 0.78, 1.56, 5.8, 3.7, C.pale, 0.12);
txt(s, 'E3 / S0', 1.12, 1.83, 5.0, 0.45, 25, C.navy, true);
txt(s, '4 correct  ·  4 wrong  ·  9 abstain', 1.12, 2.57, 5.0, 0.7, 22);
txt(s, 'Weighted coverage 67.1%\nAnswered accuracy 59.2%', 1.12, 3.48, 5.0, 1.1, 19);
rect(s, 6.83, 1.56, 5.8, 3.7, 'F8EBE8', 0.12);
txt(s, 'E4 / all strategies', 7.17, 1.83, 5.0, 0.45, 25, C.navy, true);
txt(s, '6 correct  ·  8 wrong  ·  3 abstain', 7.17, 2.57, 5.0, 0.7, 22);
txt(s, 'Weighted coverage 89.0%\nAnswered accuracy 40.0%', 7.17, 3.48, 5.0, 1.1, 19);
txt(s, 'S0, S1, S2, simple gate and ANM-only made the same 17 E4 decisions.',
  0.75, 5.78, 11.95, 0.7, 20, C.navy, true);
note(s, 'Matched case comparison. E4 adds a diagnostic to E3; all E4 model arrows match ANM. Source: archived original pilot and rescored analysis.');

s = base('ANM: synthetic success did not transfer', 7);
line(s, '128-row panel', '20 correct / 8 wrong / 4 abstain on 32 compatible synthetic cases; frozen gate failed', 1.66, C.gray);
line(s, '512-row panel', '26 correct / 0 wrong / 6 abstain on 32 new compatible synthetic cases', 3.0, C.teal);
line(s, 'Real validation', '13 correct / 13 wrong / 12 abstain on 38 pairs; weighted accuracy 48.1%', 4.34, C.red);
txt(s, 'Real outcomes are opened. They cannot confirm a method tuned after inspection.',
  0.75, 5.93, 11.8, 0.62, 19, C.navy, true);
note(s, 'Sources: artifacts/anm-experiments-2026-11-18, docs/reviews/anm-independent-validation.md. Real sample sizes 109–512; benchmark references may be imperfect.');

s = base('Checker: process validity, limited release benefit', 8);
line(s, 'Accepted', '6 reference-correct and 9 wrong upstream answers', 1.68, C.teal);
line(s, 'Rejected', '2 reference-correct and 3 wrong upstream answers', 2.9, C.red);
line(s, 'Detected', 'Unavailable E1 evidence and two E3 row-value mismatches', 4.12);
txt(s, 'E4: 17 checks passed; 14 answers released; no directional change.',
  0.75, 5.52, 11.9, 0.75, 23, C.navy, true);
note(s, '68 cached S1 checks; 48 upstream abstentions. Two strict text/structured mismatches illustrate free-text blind spots. Source: artifacts/final-delivery/track-b-diagnostics/checker-audit.json.');

if (integrated) {
  const metric = (p, c) => integrated.metrics.find(x => x.package === p && x.condition === c);
  const e3 = metric('E3', 'S0');
  const e4 = metric('E4', 'S0');
  const format = x => `${(100*x).toFixed(1)}%`;
  const answered = x => x == null ? 'undefined' : format(x);
  s = base('Larger matched real-data panel', 9);
  txt(s, '38 pairs in 12 source groups · exploratory, opened ANM labels', 0.75, 1.47, 11.8, 0.52, 21, C.navy, true);
  rect(s, 0.78, 2.20, 5.8, 2.68, C.pale, 0.12);
  txt(s, 'E3 / S0', 1.10, 2.49, 5.0, 0.4, 24, C.navy, true);
  txt(s, `${e3.correct_count} correct · ${e3.wrong_count} wrong · ${e3.abstain_count} abstain`, 1.10, 3.11, 5.0, 0.55, 19);
  txt(s, `Coverage ${format(e3.coverage)}  ·  Answered accuracy ${answered(e3.selective_accuracy)}`, 1.10, 3.95, 5.0, 0.67, 17);
  rect(s, 6.83, 2.20, 5.8, 2.68, 'F8EBE8', 0.12);
  txt(s, 'E4 / S0', 7.15, 2.49, 5.0, 0.4, 24, C.navy, true);
  txt(s, `${e4.correct_count} correct · ${e4.wrong_count} wrong · ${e4.abstain_count} abstain`, 7.15, 3.11, 5.0, 0.55, 19);
  txt(s, `Coverage ${format(e4.coverage)}  ·  Answered accuracy ${answered(e4.selective_accuracy)}`, 7.15, 3.95, 5.0, 0.67, 17);
  txt(s, `E4 S0 matched ANM on ${integrated.e4_s0_agrees_with_anm_count}/38 cases. Checker rejected ${integrated.checker.suppressed_correct} correct and ${integrated.checker.suppressed_wrong} wrong S1 answers.`,
    0.75, 5.45, 11.9, 0.95, 19, C.navy, true);
  note(s, 'Source: artifacts/final-delivery/postmerge-track-b/integrated-38-analysis/metrics.json. Labels had been opened for numerical ANM validation. 51 saved live responses were reused with exact request binding; the rest were new live calls.');
}

s = base('Conclusion and failure boundary', integrated ? 10 : 9, true);
txt(s, 'Typed evidence can be audited.\nWrong diagnostic arrows still propagate.',
  0.75, 1.78, 11.7, 1.55, 32, C.white, true);
txt(s, 'Our evidence supports process checking on this cohort. It does not support a general improvement in causal direction accuracy.',
  0.75, 3.75, 11.55, 1.06, 22, 'D9E9E6');
txt(s, 'Next valid test: a new source-separated holdout after any method revision.',
  0.75, 5.47, 11.6, 0.7, 20, 'BFD7D1');
note(s, 'Limits: one model, grouped real-data cohorts, no fresh post-validation holdout, fallible benchmark arrows, checker free-text blind spot.');

pptx.writeFile({ fileName: output });
