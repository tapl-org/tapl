# TAPL: Types and Programming Languages

<!--
Part of the TAPL project, under the Apache License v2.0 with LLVM
Exceptions. See /LICENSE for license information.
SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
-->

<p align="center">
  <a href="#what-is-tapl">What is TAPL?</a> |
  <a href="#language-goals">Goals</a> |
  <a href="#project-status">Status</a> |
  <a href="#getting-started">Getting started</a> |
  <a href="#join-us">Join us</a>
</p>

## What is TAPL? 

TAPL is a new syntax extendable programming language frontend with high-order type system. TAPL is still under development, and it is considered to be an experimental.

TAPL is named after ["Types and Programming Languages" by Benjamin C. Pierce ](https://www.cis.upenn.edu/~bcpierce/tapl/) book.

This is not an officially supported Google product.

## Language goals

Experiment and explore the following programming language features:
* Add new language syntax on the fly. So developers can extend the language by adding their own new syntax by writing their own parser.
* Run the code partially in lambda calculus engine first, then compile it to machine code.
* Support static and dynamic typings together.
* Support 4 combinations of term and type operations:
  * term ⭢ term: regular function
  * type ⭢ term: polymorphism (aka System F)
  * type ⭢ type: type operators (aka Type constructors)
  * term ⭢ type: dependent types
* Support Substructural Type Systems
* Support high-order type system (value -> type -> kind/sort)


## Project status

Tapl is currently an experimental project. There is no working compiler or toolchain.

## Getting started

As there is no compiler yet, there is no way to try out yet. We will be adding new information to this section as it becomes available.

## Join us

We'd love to have folks join us and contribute to the project. Tapl is committed to a welcoming and inclusive environment where everyone can contribute.
* Most of Tapl's design discussions occur on [Discord](https://discord.gg/7N5Gp85hAy).