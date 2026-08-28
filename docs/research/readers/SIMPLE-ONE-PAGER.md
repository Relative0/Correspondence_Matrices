# Correspondence Matrices — simple one-pager

[Research library](../README.md) · Generated reading edition, 2026-08-28.

Derived from the authored explainer and its saved evidence. Charts and interactive controls remain in the downloaded HTML.

Latest follow-up: [verified Runpod memory smoke](RUNPOD-MEMORY-SMOKE.md). This does not establish general CM dominance or production estimator acceptance.

## The problem

A Boolean expression is a rule built from conditions that are each either true or false: *this user is an admin AND the account is not suspended*. Evaluating it once, for one specific case, is easy. The hard questions are about *all possible cases*: is there any combination of inputs that lets this through? Do these two rules always agree? Which condition is actually doing the work?

Those questions are hard because the number of combinations doubles with every condition you add. Twenty conditions is a million cases; forty is a trillion. Every field below has some version of this problem, and each has built its own tools for it.

## What a CM retains

A truth table answers *what are the outputs?* You list every combination of inputs and write down what comes out. It is complete, and for a fixed variable ordering it pins the function down exactly.

A Correspondence Matrix answers a different question: *what operator produced those outputs, and what is its structure?* Same function, same answers — but now the operator is an object you can hold, compare, decompose, and store.

## The size that matters

Here is the single most important idea for reading any chart on this site. Suppose a system has 32 variables available, and you write the expression `x2 AND x17`.

Two variables matter. The other thirty do not appear and cannot change the answer. The meaningful output is four rows — every combination of two variables. The *ambient* truth table over all 32 variables has 4,294,967,296 rows, but 4,294,967,292 of them are copies of those same four answers.

So the honest measure of how big a job is is not how many variables exist. It is how many variables *actually change the answer*. This project calls that number `live_k`, and it is the horizontal axis of essentially every chart here.

## Choose the right tool

Compare a calculator, a spreadsheet, and a proof. All three deal with numbers. Asking which is *fastest* is a malformed question — they produce different outputs and answer different questions. The Boolean toolbox is in the same position.

The useful question is not “which is best?” but “what am I actually asking for?” If you want a specific answer, you want something that computes it. If you want a guarantee that covers every case at once, you want something that reduces the rule to a standard shape, or a solver. If you want the smallest circuit, you want a minimiser.

## Where reuse might help

### Good fit

The same Boolean structure is evaluated, restricted, transformed, or compared many times.

Operator or subexpression lineage matters after the first answer is produced.

Version differences and partial contexts are first-class workflow objects.

The semantic support is bounded enough for the required explicit artifact, or the CM is used as a structural layer rather than forced to enumerate everything.

### Poor fit

The job is a one-off complete evaluation where BitSet's low setup cost dominates.

The only question is whether one satisfying assignment exists; SAT is built for that.

A canonical symbolic graph under a fixed variable order is the required artifact; ROBDD/CUDD already supplies it.

The workload needs general quantum-state, numeric, probabilistic, or continuous computation rather than a Boolean structural layer.

## What is measured

Hardware/formal-verification expressions and bounded real feature-model slices have been tested. Neither establishes deployed-workflow advantage, and the feature-model performance comparisons retain documented measurement gaps. Every other field below remains a candidate whose CM-specific benefit needs a real trace and a direct incumbent comparison.
