"""Seven self-contained CM lessons. New authoring source; historical reels untouched."""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent / 'deep_series/foundational_cm_tutorial_series_v1'
LESSONS = []

def lesson(slug, title, objective, prerequisite):
    item = dict(id=f'{len(LESSONS)+1:02d}_{slug}', title=title, objective=objective,
                prerequisite=prerequisite, scenes=[])
    LESSONS.append(item)

def cue(title, text, visual, note, **data):
    LESSONS[-1]['scenes'].append(dict(title=title, text=text, visual=visual, note=note, **data))

lesson('truth_table_to_matrix', 'From a truth table to a CM',
       'Read a two-input operator matrix and explain why there are sixteen.', 'No matrix background required.')
cue('A rule with two yes-or-no inputs',
    'Imagine a door that opens only when your pass is valid and your access is enabled. Call those two facts X and Y. One means yes, and zero means no. The rule is X and Y.',
    'door', 'AND requires both inputs.', step=0)
cue('List every possible situation',
    'Two yes-or-no inputs give four situations. Both are yes; only X is yes; only Y is yes; or neither is yes. A truth table records the answer in every situation, so no case is left out.',
    'truth', 'Four input cases; one output for each.', step=0, rule='and')
cue('Evaluate the rule',
    'For this door, only the first situation opens it. The other three give zero. These four output bits describe the entire rule. A single bit, by itself, describes just one situation.',
    'truth', 'Complete rule: 1, 0, 0, 0.', step=1, rule='and')
cue('Give each input an axis',
    'Now arrange the same answers in a square. X chooses the row. Y chooses the column. Here we use the paper convention: one comes before zero on both axes. Watch the both-yes answer move to their intersection.',
    'truth', 'X selects a row. Y selects a column.', step=2, rule='and', select=[0,0])
cue('Read one cell',
    'Suppose your pass is valid, but access is disabled. That means X is one and Y is zero. Follow the top row to the right-hand column. The zero there says the door stays closed.',
    'truth', 'X = 1, Y = 0 → output 0.', step=2, rule='and', select=[0,1])
cue('Change the rule, keep the axes',
    'For a different door, either condition might be enough. That is OR. The axes stay where they are, but two more answers become one. The matrix represents the rule only when we also know what its axes mean.',
    'truth', 'OR accepts either input, including both.', step=2, rule='or')
cue('Why exactly sixteen?',
    'How many two-input rules could we make? Each of the four cells can independently contain zero or one. Two choices, four times, gives sixteen complete Boolean functions. AND and OR are two members of that family.',
    'sixteen', '2 × 2 × 2 × 2 = 16 complete functions.', step=0)
cue('Your turn: read the pattern',
    'Try this matrix. Its ones are in the two off-diagonal positions. Read the axis labels and decide: does the rule accept inputs that agree, or inputs that differ? Take a few seconds to trace both ones.',
    'truth', 'Which input pairs produce 1?', step=2, rule='xor', question=True, pause=5)
cue('Answer: the inputs differ',
    'It accepts inputs that differ. This is exclusive-or. One and zero gives one; zero and one also gives one. Equal inputs give zero. Throughout these lessons, the double vertical arrow is our written symbol for exclusive-or.',
    'truth', 'X ⇕ Y: true exactly when X and Y differ.', step=2, rule='xor')
cue('Same rule, different ordering',
    'The project website places zero before one in its introductory example. With that ordering, the AND entry is at the bottom right. Nothing about the door has changed. Both axes were reordered. Always check the labels before comparing matrices.',
    'orders', 'Read axis labels before comparing grids.')
cue('What you can now do',
    'You can now turn a truth table into a matrix and retrieve an answer from it. Next we will build whole matrices from four simple pieces. Keep the row and column labels attached as we do.',
    'truth', 'Next: four pieces that build every 2×2 operator.', step=2, rule='and')

lesson('basis_and_selection', 'Build and read a matrix with vectors',
       'Distinguish a column-times-row outer product from selecting one matrix entry.', 'Lesson 1: labelled 2×2 operator matrices.')
cue('Build the two accepting positions',
    'Exclusive-or accepts two input pairs. We can build its matrix one accepting position at a time. This lesson explains the column and row notation used for those pieces, starting with a single highlighted position.',
    'basis', 'Goal: build the two off-diagonal ones.', step=0)
cue('A column that selects the first position',
    'Ket one is a column containing one above zero. Ket zero contains zero above one. The vertical arrangement matters: these are columns with two entries. Their names tell us which input state they select in our true-first ordering.',
    'vectors', 'Ket = column. State 1 comes first.', step=0)
cue('Turn the column into a row',
    'Transpose a column and it becomes a row. We call that row a bra. Bra zero contains zero followed by one. The angled brackets are names for these vectors; we are still doing a concrete calculation with zeros and ones.',
    'vectors', 'Bra = transposed row.', step=1)
cue('Column times row makes a matrix',
    'Multiply ket one by bra zero. Every column entry multiplies every row entry. The first row becomes zero, one. The second becomes zero, zero. This is an outer product: a column times a row produces a matrix.',
    'outer', 'A 2×1 column times a 1×2 row gives a 2×2 matrix.', step=0)
cue('Four pieces, four positions',
    'Choosing either ket and either bra gives four possible pieces. Each contains exactly one one. Its ket chooses the row and its bra chooses the column. These four single-position matrices are the basis pieces for our two-input operators.',
    'basis', 'Each basis matrix marks one input pair.', step=1)
cue('Combine the pieces for exclusive-or',
    'Choose the top-right piece and the bottom-left piece. Combine their entries with exclusive-or. Because their ones occupy different cells, both ones remain. We have reconstructed the complete exclusive-or matrix from its two accepting input pairs.',
    'basis', '|1⟩⟨0| ⇕ |0⟩⟨1| gives the XOR matrix.', step=2)
cue('Selecting an answer is a different operation',
    'To read the finished matrix, place a bra on its left and a ket on its right. The left vector selects a row. The right vector selects a column. This time the result is one number: the entry at their intersection.',
    'selection', 'Row selector · matrix · column selector → one bit.', step=0)
cue('Your turn: select a cell',
    'Use the exclusive-or matrix. Put bra zero on the left and ket one on the right. Which row and column does that select? What answer should come out? Follow the labels before you calculate.',
    'selection', 'Evaluate ⟨0| M⇕ |1⟩.', step=1, question=True, pause=5)
cue('Answer: bottom row, first column',
    'Bra zero selects the bottom row. Ket one selects the first column. Their intersection contains one, as expected for two different inputs. An outer product builds a grid; the row-matrix-column calculation reads one entry from a grid.',
    'selection', '⟨0| M⇕ |1⟩ = 1.', step=2)
cue('Operand order can change the rule',
    'One last check: X implies Y fails only when X is true and Y is false. Reverse the implication and the failing case changes. Keep the axes fixed and the zero moves. Swapping the operands is not the same operation as relabelling an axis.',
    'implications', 'X → Y and Y → X are different rules.')

lesson('logical_matrices', 'Expressions first, values second',
       'Evaluate an expression-valued LM and distinguish it from a numeric CM.', 'Lessons 1–2: Boolean rules and outer products.')
cue('Let a cell hold a recipe',
    'So far, our cells have held finished answers: zero or one. A logical matrix, or L M, holds expressions instead. Think of each cell as a small recipe that still needs values for its variables.',
    'lm', 'LM cells contain expressions.', step=0)
cue('Build an expression column and row',
    'Place X and not X in a column. Place Y and not Y in a row. Here not reverses a Boolean value. Multiplication in this logical construction means AND: both factors must be true for the product to be true.',
    'lm', 'Here juxtaposition means AND; ¬ means NOT.', step=1)
cue('Write all four expressions',
    'Their outer product gives four expressions. The top-left cell is X and Y. The top-right is X and not Y. The bottom row uses not X instead. We write M sub X Y equals this whole two-by-two logical matrix.',
    'lm', 'M_XY names the complete 2×2 LM.', step=2)
cue('Choose the positive assignment',
    'For the positive assignment used here, set the original variables X and Y to one. Then not X and not Y become zero. Apply that same assignment to every expression. We are evaluating one symbolic object consistently, cell by cell.',
    'lm', 'X = Y = 1; therefore ¬X = ¬Y = 0.', step=3)
cue('Evaluate the first row',
    'The top-left expression becomes one and one, which is one. The top-right becomes one and zero, which is zero. Notice that the written expressions stay different even though we gave the original variables the same value.',
    'lm', 'X∧Y → 1. X∧¬Y → 0.', step=4)
cue('Evaluate the second row',
    'Both bottom expressions contain not X, now zero, so both evaluate to zero. The resulting numeric matrix is the AND operator in true-first order. The paper describes this relationship as taking the positive valuation of the logical matrix.',
    'lm', 'Positive valuation: expression LM → numeric CM.', step=5)
cue('A different LM gives a different operator',
    'To represent equivalence, start from the equivalence logical matrix shown here. Its diagonal entries test agreement. Its off-diagonal entries test exclusive-or. We changed the expressions before evaluating them; valuation alone did not change AND into equivalence.',
    'equivalence_lm', 'Change the LM first; then apply the assignment.', step=0)
cue('Your turn: evaluate an off-diagonal cell',
    'Again set X and Y to one. What does the upper-right exclusive-or expression evaluate to? And what does an equivalence expression on the diagonal evaluate to? Work out those two cases before viewing the completed matrix.',
    'equivalence_lm', 'At X = Y = 1: X ⇕ Y = ?  X ↔ Y = ?', step=1, question=True, pause=5)
cue('Answer: agreement on the diagonal',
    'Exclusive-or is zero because the inputs agree. Equivalence is one for the same reason. So the diagonal entries become one and the other entries become zero. The original expressions determine which operator the valuation produces.',
    'equivalence_lm', 'Equivalence CM: ones on the diagonal.', step=2)
cue('Keep the two layers separate',
    'You now have two useful layers: expressions while constructing a logical matrix, and bits after evaluating it. Next we will combine two complete logical matrices. Keeping their names and their entries separate will make that larger construction much easier to read.',
    'lm', 'Next: combine two complete LMs.', step=5)

lesson('tensor_construction', 'Two logical matrices become a 4×4',
       'Expand a tensor product and identify its full row and column components.', 'Lesson 3: expression-valued matrices.')
cue('Combine two pairs of variables',
    'Suppose one logical matrix uses W and X, and another uses Y and Z. How do we keep every combination of their entries? A tensor product gives a systematic answer. We will build the entire four-by-four grid, one block at a time.',
    'tensor', 'Each factor is a complete 2×2 logical matrix.', step=0)
cue('Read the two equalities',
    'M sub W X is the whole matrix on the left of the tensor symbol. M sub Y Z is the whole matrix on the right. The equals signs connect each name to its four expressions. W X inside the first matrix is only one entry.',
    'tensor', 'Matrix names and individual entries have different roles.', step=1)
cue('Each entry expands into a block',
    'For an ordinary block expansion, take each entry of the first matrix and combine it with every entry of the second. There are two block rows and two block columns. Each block has two rows and two columns, giving four of each overall.',
    'tensor', '2 block rows × 2 rows per block = 4 rows.', step=2)
cue('Inspect the first block',
    'Begin with the first block. Every expression there includes W and X. The second matrix contributes Y and Z, Y and not Z, not Y and Z, or neither. These four combinations occupy a square, with two entries in each row.',
    'tensor', 'The highlighted region contains four expressions.', step=3, block=[0,0])
cue('Fill the remaining blocks',
    'The next block uses W and not X. The two lower blocks use not W. In each case the second matrix contributes all four of its expressions. Now the complete grid contains sixteen expressions, covering all combinations of the four variables.',
    'tensor', 'All four blocks belong to M_WX ⊗ M_YZ.', step=4)
cue('Understand the row labels',
    'Why do the rows use W and Y? Each row combines a row choice from the first matrix with a row choice from the second. Each column similarly combines X and Z. The row components and column components are written separately above the grid.',
    'tensor', 'Rows combine W,Y. Columns combine X,Z.', step=5)
cue('Trace one expression across the grid',
    'Follow row W and not Y, then column not X and Z. The intersection contains W, not X, not Y, and Z, joined by AND. The axis components tell you every factor in that expression without memorising the grid.',
    'tensor', 'W∧¬Y with ¬X∧Z → W∧¬X∧¬Y∧Z.', step=5, select=[1,2])
cue('Your turn: the final expression',
    'Find the last row and the last column. Which of the four variables are negated at that intersection? Read the row components first, then the column components. You can pause here if you want more time.',
    'tensor', 'What expression belongs in the bottom-right cell?', step=5, select=[3,3], question=True, pause=5)
cue('Answer: all four are negated',
    'All four variables are negated. The row contributes not W and not Y. The column contributes not X and not Z. Joined together, they give the final expression shown. This is one entry of the full tensor, not the tensor itself.',
    'tensor', '¬W∧¬X∧¬Y∧¬Z.', step=5, select=[3,3])
cue('The scaffold is ready',
    'This base tensor organises conjunction expressions. To construct a more interesting compound rule, we must supply the appropriate logical matrices and combine them according to that rule. The next lesson does that for exclusive-or followed by implication.',
    'tensor', 'Next: use this structure to build a compound rule.', step=5)

lesson('compound_rule', 'Build and check a four-variable rule',
       'Construct the paper example and verify a cell directly from its Boolean rule.', 'Lessons 1–4, especially tensor block order.')
cue('Start with the meaning of the rule',
    'Consider this rule: if W and X differ, then Y must be false and Z must be true. The left condition is exclusive-or. The right condition is not Y and Z. We want a matrix containing the answer for every four-variable assignment.',
    'compound', 'If W and X differ, require ¬Y∧Z.', step=0)
cue('Make the implication test explicit',
    'Call the two conditions P and Q for a moment. P implies Q fails only when P is one and Q is zero. If the requirement is triggered and not met, the whole rule is false. Every other pair is accepted.',
    'compound', 'Only P = 1, Q = 0 is rejected.', step=1)
cue('Build each condition first',
    'After positive valuation, the first condition has the exclusive-or matrix, which we call A. The second has matrix B, with its one at Y false and Z true. These are separate two-by-two matrices for the two parts of the rule.',
    'compound', 'A represents W ⇕ X. B represents ¬Y∧Z.', step=2)
cue('Accept the first case',
    'The first accepted case has both conditions true. The tensor A with B marks exactly those four-variable assignments. Each one indicates a place where the left condition and the right condition both return one.',
    'compound', 'Accepted case 1: P = 1, Q = 1.', step=3)
cue('Accept the second case',
    'The second case has the left condition false and the right condition true. Flip every bit of A, then tensor that complement with B. Complement here means entrywise Boolean NOT: every zero becomes one, and every one becomes zero.',
    'compound', 'Accepted case 2: P = 0, Q = 1.', step=4)
cue('Accept the third case',
    'The third accepted case has both conditions false. Tensor the complement of A with the complement of B. The three accepted cases cannot overlap, because each assignment gives only one pair of values for P and Q.',
    'compound', 'Accepted case 3: P = 0, Q = 0.', step=5)
cue('Combine the accepted cases',
    'Combine the three tensors entry by entry using exclusive-or. Since they do not overlap, each accepted assignment keeps one one. This produces the four-by-four matrix from the paper. Its displayed row components are W, Y, and its column components are X, Z.',
    'compound', '(A⊗B) ⇕ (¬A⊗B) ⇕ (¬A⊗¬B).', step=6)
cue('Your turn: find a failing assignment',
    'Test W, X, Y, Z equal to zero, one, one, one. Does the implication pass or fail? First evaluate its two conditions directly. Then locate the matching row and column in the matrix. Take a moment to do both checks.',
    'compound', 'WXYZ = 0111. What is the output?', step=7, question=True, pause=5)
cue('Check the logic first',
    'W and X differ, so P is one. But Y is true, so not Y and Z is zero. A true condition implies a false requirement, which fails. The expected output is zero.',
    'compound', 'P = 0 ⇕ 1 = 1. Q = ¬1∧1 = 0. Result: 0.', step=8)
cue('Check the address second',
    'The row uses W and Y, giving zero, one. The column uses X and Z, giving one, one. In our descending order this selects the third physical row and the first column. Their intersection is zero, agreeing with the direct calculation.',
    'compound', 'Row WY = 01. Column XZ = 11. Cell = 0.', step=9)
cue('A note on the paper’s bra notation',
    'The paper writes its row selector with the bra factors in reversed written order, Y then W. That notation needs its component expansion. Our explicit row labels keep W and Y visible in the physical order used by the displayed matrix.',
    'paper_order', 'Physical row components WY; written paper bra factors ⟨Y|⟨W|.')
cue('Two checks are better than one',
    'You have now constructed the matrix and checked an entry without trusting the picture alone. Next we will use the repository layout convention, where zero comes first and binary input groups become ordinary numeric addresses.',
    'compound', 'Direct rule evaluation and matrix lookup must agree.', step=9)

lesson('repository_lookup', 'Find a cell in the repository layout',
       'Split an assignment, convert binary groups to indices, and check the stored output.', 'Lesson 1; lessons 2–5 are optional for this repository path.')
cue('One address, one answer',
    'Suppose a rule combines four yes-or-no inputs, A, B, C, and D. A repository explicit C M layout stores its answers in an ordered grid. To read one answer, we need to know which inputs select rows and which select columns.',
    'repo', 'R = [A,B]. C = [C,D].', step=0)
cue('Give the rule a concrete meaning',
    'Our rule asks whether two checks disagree. The first check is A and B: both must be true. The second is C or D: at least one must be true. Exclusive-or returns one when exactly one of these two checks passes.',
    'repo', 'F = (A∧B) ⇕ (C∨D).', step=1)
cue('Declare the order before looking up',
    'Use A and B for rows, and C and D for columns. The repository orders each group as zero-zero, zero-one, one-zero, one-one. The first bit is the more significant bit, so the corresponding numeric indices are zero, one, two, three.',
    'repo', 'Ascending binary order; indices start at 0.', step=2)
cue('Split the assignment',
    'Take assignment one-zero-one-one in A, B, C, D order. Split it according to our declared groups. A B is one-zero, and C D is one-one. These groups identify a row and a column; they are not yet the output.',
    'repo', 'ABCD = 1011 → AB = 10, CD = 11.', step=3, bits='1011')
cue('Convert the row group',
    'For a two-bit binary group, the first position has weight two and the second has weight one. Row bits one-zero mean one times two plus zero times one. That gives row index two, the third displayed row.',
    'repo', 'Row: 1×2 + 0×1 = 2.', step=4, bits='1011')
cue('Convert the column group',
    'Column bits one-one mean one times two plus one times one. That gives column index three, the fourth displayed column. Follow the selected row and column to their intersection. We have found the location for this assignment.',
    'repo', 'Column: 1×2 + 1×1 = 3.', step=5, bits='1011')
cue('Explain the stored value',
    'Now evaluate the rule. A and B is one and zero, giving zero. C or D is one or one, giving one. The two checks differ, so exclusive-or returns one. That is the value stored at row two, column three.',
    'repo', '(1∧0) ⇕ (1∨1) = 0 ⇕ 1 = 1.', step=6, bits='1011')
cue('Your turn: a second assignment',
    'Try one-one-one-zero. Split the bits into the same two groups, find their indices, and decide the output. Be careful: the selected column contains a one bit, but that does not by itself determine whether the whole rule is true.',
    'repo', 'ABCD = 1110. Find row, column, and output.', step=3, bits='1110', question=True, pause=5)
cue('Answer: two passing checks disagree?',
    'A B is one-one, so choose row three. C D is one-zero, so choose column two. Both component checks return one. They agree, so exclusive-or returns zero. The cell at row three, column two confirms that answer.',
    'repo', '(1∧1) ⇕ (1∨0) = 1 ⇕ 1 = 0.', step=6, bits='1110')
cue('Check the both-false case too',
    'One more example: zero-one-zero-zero. The row group gives index one, and the column group gives index zero. A and B is false, and C or D is false. Equal results again give zero. Exclusive-or rejects both agreement cases.',
    'repo', '(0∧1) ⇕ (0∨0) = 0 ⇕ 0 = 0.', step=6, bits='0100')
cue('A repeatable lookup method',
    'The method is always the same: read the declared variable order, split the assignment, convert each group, and select the intersection. Evaluating the original rule gives an independent check. Next we will change the split while keeping every answer the same.',
    'repo', 'Declare → split → index → select → check.', step=6, bits='0100')

lesson('repartition', 'Change the layout, keep the function',
       'Track one assignment through 4×4, 2×8, and 8×2 layouts.', 'Lesson 6: binary indexing and the running four-input rule.')
cue('A different-shaped address book',
    'Our four-input rule has sixteen possible assignments. Must its answers always form a square? In the repository, no. We can assign different numbers of variables to the row and column groups, while keeping the same Boolean function.',
    'repartition', 'Same rule F = (A∧B) ⇕ (C∨D).', step=0)
cue('Count the rows and columns',
    'Each row variable doubles the number of row combinations. Two row variables give four rows. Two column variables give four columns. That is our familiar four-by-four layout, containing sixteen output entries altogether.',
    'repartition', '2² rows × 2² columns = 16 cells.', step=0)
cue('Move B to the column group',
    'Now put only A in the row group, and put B, C, D in the column group, in that order. One row bit gives two rows. Three column bits give eight columns. The new two-by-eight rectangle still has sixteen entries.',
    'repartition', 'R = [A]. C = [B,C,D]. Shape: 2×8.', step=1)
cue('Follow the same assignment',
    'Follow one-zero-one-one again. A alone gives row index one. The remaining bits, B C D, are zero-one-one. Their weights are four, two, and one, so the column index is three. The selected entry remains one.',
    'repartition', '1011 → row 1, column 3 → output 1.', step=1, select=True)
cue('Move C to the row group instead',
    'For an eight-by-two layout, use A, B, C as row variables and D as the column variable. Three row bits give eight rows. One column bit gives two columns. Again the product is sixteen, covering the same assignments.',
    'repartition', 'R = [A,B,C]. C = [D]. Shape: 8×2.', step=2)
cue('Recompute the address',
    'Our assignment now has row bits one-zero-one, worth four plus zero plus one: index five. Column bit one gives index one. The cell still contains one. Its address changed because the variable groups changed; its Boolean answer did not.',
    'repartition', '1011 → row 5, column 1 → output 1.', step=2, select=True)
cue('Your turn: track a zero',
    'Use assignment one-one-one-zero and the two-by-eight layout. What is its new row index? What is its new column index? You already know the rule returns zero for this assignment. Find where that zero belongs now.',
    'repartition', 'In the 2×8 layout: 1110 → (?, ?) → 0.', step=1, bits='1110', question=True, pause=5)
cue('Answer: row one, column six',
    'A gives row one. B C D is one-one-zero, worth four plus two plus zero: column six. The entry is zero. The old four-by-four address was row three, column two. Both addresses refer to the same complete input assignment.',
    'repartition', '1110 → row 1, column 6 → output 0.', step=1, bits='1110', select=True)
cue('What is preserved?',
    'To check a repartition, compare answers for matching assignments, not matching physical positions. Every assignment must retain its output. With four variables we can check all sixteen directly. A new shape does not reduce the number of explicit answers.',
    'repartition', 'All 16 assignments preserve their outputs.', step=3)
cue('Know what this lesson establishes',
    'These rectangles belong to the repository row-column layout convention. The paper tensor construction we studied was square. The examples here demonstrate addressing and representation. They do not, by themselves, show a speed advantage or a smaller total output.',
    'repartition', 'Shape changes; function and 16-cell count remain.', step=3)
cue('You can now follow the whole path',
    'You can now read a Boolean rule, understand its matrix entries, construct larger paper examples, and track repository assignments through different layouts. When a grid looks confusing, begin with its variable groups and ordering. They are the key to making every cell meaningful.',
    'repartition', 'Rule → labelled matrix → assignment → checked answer.', step=3)

def export():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'CURRICULUM_V1.json').write_text(json.dumps(LESSONS,ensure_ascii=False,indent=2),encoding='utf-8')
    for l in LESSONS:
        folder=OUT/l['id']; folder.mkdir(exist_ok=True)
        lines=[f"# {l['title']}", '', f"Objective: {l['objective']}", '', f"Prerequisite: {l['prerequisite']}"]
        for i,s in enumerate(l['scenes'],1):
            lines += ['',f"## {i}. {s['title']}",'',s['text'],'',f"Visual: `{s['visual']}`. {s['note']}"]
            if s.get('pause'): lines += ['',f"Hold question for {s['pause']} seconds of silence; answer hidden."]
        (folder/'SCRIPT_AND_VISUAL_SPEC_V1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'lessons':len(LESSONS),'scenes':sum(len(l['scenes']) for l in LESSONS), 'speech_characters':sum(len(s['text'])+2 for l in LESSONS for s in l['scenes'])}))

if __name__=='__main__': export()
