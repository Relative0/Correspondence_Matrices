# D4 Project

D4 is a library designed to compute model counts of logical formulas. It currently supports CNF and circuit-based formats, and can be integrated into custom applications for advanced reasoning and model enumeration tasks.

This README provides an overview of how to use the D4 library, the supported input formats, and example usage.

---

## Supported Methods

D4 supports various methods to analyze and count models of logical formulas. More detailed documentation on the methods used internally (e.g., decision diagrams, SAT solvers, etc.) will be added soon.

---

## How to Use

D4 is implemented as a library and should be linked into a separate executable for use. A demo executable is provided to demonstrate basic functionality.

To run a simple counter example on a CNF file:

```bash
cd demo/counter
./build.sh
./build/counter -i ../../instancesTest/cnfs/cnf5.cnf
```

To count models of a circuit-based input, see the example under the `circuit` section below.

---

## Input Formats

### 1. Circuit Format

D4 supports a custom circuit format (BC-S1.2), where formulas are defined in terms of logic gates and evaluation constraints. This format allows complex Boolean functions to be represented more directly than CNF.

#### Format Description

A BC-S1.2 file consists of:

* **Comments**: Prefixed with `c`
* **Weight Information** (optional): `c w <literal> <weight>`
* **Input Variables**: `I <var>`
* **Gate Definitions**: `G <var> := <formula>`
* **Target Literals**: `T <literal>`

#### Formula Syntax

A gate's formula can be one of:

* `A <lit1> <lit2> ...` – AND
* `O <lit1> <lit2> ...` – OR
* `I <lit>` – Identity (can also represent negation using `-<lit>`)

> A literal is either a variable or its negation (e.g., `x`, `-x`).

#### Example 1: Single Negative Literal

```plaintext
c BC-S1.2
I x
T -x
```

#### Example 2: Complex Formula `(a & b) | -(-c & b)`

```plaintext
c BC-S1.2
I a
I b
I c
G g1 := A a b
G g2 := A -c b
G g3 := O g1 -g2
T g3
```

#### Run Example

To run the model counter on a circuit:

```bash
./build/counter -i ../../instancesTest/circuits/circ1.bc --input-type circuit
```

---

### 2. CNF Format

D4 also supports the standard **DIMACS CNF** format. This is widely used in SAT solving and describes Boolean formulas as a conjunction of clauses, each a disjunction of literals.

To run a model counter on a CNF file:

```bash
./build/counter -i ../../instancesTest/cnfs/cnf5.cnf
```
