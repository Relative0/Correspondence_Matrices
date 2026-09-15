"""Nine-lesson successor with operator faces and explicit logical measurements."""
from pathlib import Path
from copy import deepcopy
import json
import cm_tutorial_curriculum_v1 as old

OUT=Path(__file__).resolve().parent/'deep_series/foundational_cm_tutorial_series_v2'
LESSONS=[]
def scene(title,text,visual,note,**data): return dict(title=title,text=text,visual=visual,note=note,**data)
def lesson(slug,title,objective,prerequisite,scenes,reuse=None):
    l=dict(id=f'{len(LESSONS)+1:02d}_{slug}',title=title,objective=objective,prerequisite=prerequisite,scenes=scenes)
    if reuse:l['reuse_audio_from']=reuse
    LESSONS.append(l)

s=deepcopy(old.LESSONS[0]['scenes'])
s.insert(5,scene('Give the CM its operator name',
 'We put an operator symbol in square brackets to name its correspondence matrix. Bracket AND equals the array shown. If the operator is not chosen yet, bracket theta stands for its C M. Once it is chosen, the symbol and numeric array describe the same ordered object.',
 'operator_definition','[∧] names the AND CM.',step=0))
s.insert(8,scene('Impax: every input pair is accepted',
 'The all-ones matrix is tautological: every input pair produces one. Its operator is called Impax. The symbol places the exclusive-or arrow directly over the equivalence arrow, sharing the same center. Agreement and disagreement together cover every possible input pair.',
 'impax','Impax accepts every pair; its CM has four ones.'))
answer=next(i for i,x in enumerate(s) if x['title']=='Answer: the inputs differ')
s.insert(answer+1,scene('Theta stands for a chosen operator',
 'Sometimes we need a name for an operator before choosing which one. We use theta in brackets for its C M. If we choose exclusive-or, bracket theta equals bracket exclusive-or, which equals the off-diagonal numeric matrix. Theta is a placeholder, not an additional Boolean rule.',
 'operator_definition','Choose θ = ⇕, so [θ] = [⇕].',step=1))
lesson('truth_table_to_matrix','From truth tables to operator CMs','Read a CM in numeric and bracketed-operator notation.','No matrix background required.',s)

s=deepcopy(old.LESSONS[1]['scenes'][:6])
s += [scene('Your turn: place a basis entry',
 'Try building ket zero times bra one. Which row does the ket choose, and which column does the bra choose? Decide where the single one will appear. The other entries must all be zero.',
 'basis_practice','Build |0⟩⟨1|. Where does its 1 belong?',step=0,question=True,pause=5),
 scene('Answer: the lower-left basis matrix',
 'Ket zero chooses the bottom row. Bra one chooses the first column, so the one belongs at the lower left. The paper names this operator with a downward double arrow. Its matrix accepts left input false and right input true.',
 'basis_practice','|0⟩⟨1| = [⇓].',step=1),
 scene('Next: use the matrix to measure',
 'An outer product makes a matrix from a column and a row. In the next lesson, we place a row on the left of an existing C M and a column on its right. We will compute the resulting single bit, showing every AND and exclusive-or.',
 'measurement_intro','Build: column × row. Measure: row × CM × column.')]
lesson('basis_matrices','Build CMs from four basis matrices','Build a numeric basis matrix and connect it to its operator symbol.','Lesson 1: operator names and true-first axes.',s)

s=[]
def n(title,text,note,step,**kw):s.append(scene(title,text,'numeric_measurement',note,step=step,**kw))
n('A measurement you can calculate',
 'Let us calculate bra zero, bracket exclusive-or, ket one. The bracketed operator is the exclusive-or C M we already defined. The paper calls this use of a matrix with two state vectors a logical measurement. Here the result is one Boolean value.',
 '⟨0|[⇕]|1⟩: row vector · CM · column vector.',0)
n('Replace every symbol by its array',
 'Bra zero is the row zero, one. The exclusive-or C M is zero, one above one, zero. Ket one is the column one above zero. The dimensions fit: one-by-two, then two-by-two, then two-by-one. The final result has one entry.',
 '⟨0| = [0,1]. |1⟩ = [1,0]ᵀ.',1)
n('AND the pairs; XOR the terms',
 'We use the shape of matrix multiplication, but with Boolean operations. AND takes the place of multiplication. Exclusive-or combines the products in each sum. This is not ordinary integer addition, and it is not OR: one exclusive-or one is zero.',
 'Product: AND. Sum: ⇕. In particular, 1 ⇕ 1 = 0.',2)
n('First intermediate entry',
 'Start by multiplying the bra into the C M. For the first output entry, pair the bra with the first matrix column. Zero and zero gives zero. One and one gives one. Exclusive-or those two terms: zero exclusive-or one is one.',
 '(0∧0) ⇕ (1∧1) = 0 ⇕ 1 = 1.',3)
n('Second intermediate entry',
 'Now use the second matrix column. Zero and one gives zero. One and zero also gives zero. Their exclusive-or is zero. Together the two column calculations have produced the intermediate row one, zero.',
 '(0∧1) ⇕ (1∧0) = 0 ⇕ 0 = 0.',4)
n('Keep the remaining ket visible',
 'We have completed the bra-times-matrix part. The intermediate row is one, zero, and the ket on the right is still one above zero. The intermediate row is not yet the measurement result. One final row-by-column operation remains.',
 '(⟨0|[⇕])|1⟩ = [1,0] [1,0]ᵀ.',5)
n('Finish the contraction',
 'Pair the first entries: one and one is one. Pair the second entries: zero and zero is zero. Exclusive-or those products to get one. In this left-first calculation, the final terms appear as one exclusive-or zero.',
 '(1∧1) ⇕ (0∧0) = 1 ⇕ 0 = 1.',6)
n('You can calculate the right side first',
 'We can also keep the same operands and first apply the C M to the ket. Its top row produces zero, and its bottom row produces one. The intermediate object is now the column zero above one. This changes the grouping, not the input order.',
 '[⇕]|1⟩ = [0,1]ᵀ.',7)
n('The other grouping gives the same answer',
 'Bra zero is still zero, one. Pair it with that new column. The products are zero and zero, then one and one. Their exclusive-or is zero exclusive-or one, giving one. Both legal groupings agree on the measurement result.',
 '⟨0|([⇕]|1⟩) = 0 ⇕ 1 = 1.',8)
n('Your turn: change the right input',
 'Keep bra zero and the same exclusive-or C M, but replace ket one with ket zero. Ket zero is zero above one. Use the intermediate row from the left-first calculation. What single bit do you get now?',
 'Evaluate ⟨0|[⇕]|0⟩. Use |0⟩ = [0,1]ᵀ.',9,question=True,pause=5)
n('Answer: equal inputs give zero',
 'The intermediate row is still one, zero. Pair it with zero above one. Both AND products are zero, so their exclusive-or is zero. That agrees with the meaning of exclusive-or: the two input states are now both zero.',
 '(1∧0) ⇕ (0∧1) = 0 ⇕ 0 = 0.',10)
n('From a numeric answer to a symbolic rule',
 'You can now calculate a logical measurement instead of only pointing at a cell. Next we will use expression-valued state vectors with a numeric implication C M. The same arithmetic will recover the whole implication expression from the paper.',
 'Next: derive ⟨X|[⇒]|Y⟩ = X ⇒ Y.',11)
lesson('numeric_measurements','Calculate a CM measurement','Compute both groupings of ⟨0|[⇕]|1⟩ using AND and XOR.','Lessons 1–2: bracketed operators, bras and kets.',s)

s=[]
def y(title,text,note,step,**kw):s.append(scene(title,text,'symbolic_measurement',note,step=step,**kw))
y('Recover implication from its CM',
 'Under the operator table on page seven, the paper works out bra X, bracket implication, ket Y. This time X and Y remain variables. We will recover the implication expression by the same AND-and-exclusive-or calculation used in the numeric lesson.',
 'Paper, printed page 7: ⟨X|[⇒]|Y⟩.',0)
y('Define the two symbolic vectors',
 'Bra X is the row X, not X. Ket Y is the column Y above not Y. The implication C M stays numeric: one, zero above one, one. Only the state vectors contain variables at this stage.',
 '⟨X| = [X,¬X]. |Y⟩ = [Y,¬Y]ᵀ.',1)
y('Multiply into the first column',
 'For the first intermediate entry, pair X and not X with the first column, one and one. This gives X exclusive-or not X. Exactly one of a Boolean value and its negation is true, so that entry simplifies to one.',
 '(X∧1) ⇕ (¬X∧1) = X ⇕ ¬X = 1.',2)
y('Multiply into the second column',
 'The second column is zero above one. Pairing it with the same bra gives X and zero, exclusive-or not X and one. The first term vanishes; the second becomes not X. We now know both entries of the intermediate row.',
 '(X∧0) ⇕ (¬X∧1) = 0 ⇕ ¬X = ¬X.',3)
y('The intermediate row in the paper',
 'The paper writes the row as X exclusive-or not X, followed by not X. We can also write it as one, not X. These two rows are equal. Keep ket Y on the right, because the final contraction still has to be done.',
 '[X ⇕ ¬X, ¬X] = [1,¬X].',4)
y('Contract with the ket',
 'Multiply the first row entry by Y and the second by not Y, then exclusive-or the products. The result is Y exclusive-or not X and not Y. The parentheses matter: the second term requires both not X and not Y.',
 '(1∧Y) ⇕ (¬X∧¬Y) = Y ⇕ (¬X∧¬Y).',5)
y('Why XOR can become OR here',
 'These two terms cannot both be true. If Y is true, the term containing not Y is false. If that second term is true, Y is false. For these disjoint terms, exclusive-or and OR give the same result. That replacement is not valid for arbitrary overlapping terms.',
 'Y and (¬X∧¬Y) never overlap.',6)
y('Simplify to the familiar rule',
 'So we have Y or the conjunction of not X and not Y. Distribute OR over that conjunction. One factor becomes Y or not Y, which is always true. The remaining factor is not X or Y: precisely X implies Y.',
 'Y ∨ (¬X∧¬Y) = (Y∨¬X)∧(Y∨¬Y) = ¬X∨Y.',7)
y('Read the complete chain',
 'Here is the derivation together, on separate lines so each step stays readable. The numeric C M and the two symbolic vectors produce the intermediate row, then the expression, then implication. No valuation of X or Y was needed to establish this identity.',
 '⟨X|[⇒]|Y⟩ = Y ⇕ (¬X∧¬Y) = X ⇒ Y.',8)
y('Your turn: test the failing input',
 'Now choose X equal to one and Y equal to zero. Evaluate the expression not X or Y, and compare it with the appropriate entry of the implication C M. Both calculations should give the same result.',
 'X=1, Y=0: evaluate ¬X∨Y and locate its cell.',9,question=True,pause=5)
y('Answer: the one rejected input pair',
 'Not X is zero and Y is zero, so their OR is zero. In the true-first matrix, X selects the first row and Y selects the second column. The entry there is zero. This is the one case in which implication fails.',
 '¬1∨0 = 0; ⟨1|[⇒]|0⟩ = 0.',10)
y('The next layer: expressions inside the matrix',
 'In this lesson the C M was numeric, while its state vectors contained expressions. Next we move expressions into the matrix cells themselves. That is the logical-matrix layer, and we will keep it visually distinct from the numeric operator matrices you now know how to use.',
 'Next: a logical matrix has expressions in its cells.',11)
lesson('symbolic_implication','Derive the paper’s implication example','Derive the page-7 identity, including intermediate rows and simplification.','Lesson 3: numeric logical measurements.',s)

for i,l in enumerate(old.LESSONS[2:]):
    source=deepcopy(l)
    prerequisites=['Lessons 1–4: numeric CMs and symbolic state vectors.',
                   'Lesson 5: expression-valued logical matrices.',
                   'Lessons 5–6: positive valuation and tensor block order.',
                   'Lesson 1; the algebraic lessons are optional for this repository path.',
                   'Lesson 8: binary addressing and the running four-input rule.']
    lesson(l['id'][3:],l['title'],l['objective'],prerequisites[i],source['scenes'],reuse=l['id'])

def export():
    OUT.mkdir(exist_ok=True,parents=True)
    (OUT/'CURRICULUM_V2.json').write_text(json.dumps(LESSONS,ensure_ascii=False,indent=2),encoding='utf-8')
    for l in LESSONS:
        f=OUT/l['id'];f.mkdir(exist_ok=True)
        lines=[f"# {l['title']}",'',f"Objective: {l['objective']}",'',f"Prerequisite: {l['prerequisite']}"]
        for i,c in enumerate(l['scenes'],1):
            lines += ['',f"## {i}. {c['title']}",'',c['text'],'',f"Visual `{c['visual']}`: {c['note']}"]
            if c.get('pause'):lines += ['',f"Hold question for {c['pause']} seconds; answer unrevealed."]
        (f/'SCRIPT_AND_VISUAL_SPEC_V2.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(lessons=len(LESSONS),scenes=sum(len(l['scenes']) for l in LESSONS),new_voice_lessons=sum('reuse_audio_from' not in l for l in LESSONS))))

if __name__=='__main__':export()
