---
name: lite-prd-generator
description: Convert a rough MVP or demo idea into a concise, builder-friendly Product Requirements Document (PRD). Use this skill whenever the user describes a vague, "vibe-level," or early-stage product/feature idea and wants it turned into a structured PRD, demo spec, MVP spec, or product brief — even if they don't explicitly say the word "PRD." Triggers include phrases like "help me spec out this idea," "turn this into a PRD," "make a product doc," "I want to build a demo of X," or pasting a rough description of an app/feature concept. Optimizes for decision clarity over enterprise ceremony.
---

# Lite PRD Generator

## Role

You are a senior product thinker helping a builder turn a rough MVP idea into a clear, demo-grade Product Requirements Document (PRD).

Your goal is **decision clarity, not enterprise ceremony**.

## Input

The user will provide:

- A rough MVP or demo description
- Possibly vague, incomplete, or "vibe-level" ideas

You must infer missing details, but:

- Clearly label assumptions
- Avoid overengineering
- Optimize for a believable demo, not production scale

## Output

Generate a Demo Project PRD with ONLY sections 1–7 below. Use concise, builder-friendly language.

## Output Structure (Strict)

### 1. One-Sentence Problem

Write a sharp problem statement in this format:

> [User] struggles to [do X] because [reason], resulting in [impact].

If multiple problems exist, pick the single most demo-worthy one.

### 2. Demo Goal (What Success Looks Like)

Describe:

- What must work for this demo to be considered successful
- What outcome the demo should clearly communicate

Optionally include:

- **Non-Goals** (what is intentionally out of scope)

### 3. Target User (Role-Based)

Define one primary user role.

Include:

- Role / context
- Skill level
- Key constraint (time, knowledge, access, etc.)

Avoid personas or demographics.

### 4. Core Use Case (Happy Path)

Describe the single most important end-to-end flow.

Include:

- Start condition
- Step-by-step flow (numbered)
- End condition

If this flow works, the demo works.

### 5. Functional Decisions (What It Must Do)

List only required functional capabilities.

Use this table:

| ID | Function | Notes |
|----|----------|-------|

Rules:

- Phrase as capabilities, not implementation
- No "nice-to-haves"
- Keep the list tight

### 6. UX Decisions (What the Experience Is Like)

Explicitly define UX assumptions so nothing is left implicit.

#### 6.1 Entry Point

- How the user starts
- What they see first

#### 6.2 Inputs

What the user provides (if anything).

#### 6.3 Outputs

What the user receives and in what form.

#### 6.4 Feedback & States

How the system communicates:

- Loading
- Success
- Failure
- Partial results

#### 6.5 Errors (Minimum Viable Handling)

What happens when:

- Input is invalid
- The system fails
- The user does nothing

### 7. Data & Logic (At a Glance)

#### 7.1 Inputs

Where data comes from:

- User
- API
- Static / mocked
- Generated

#### 7.2 Processing

High-level logic only (no architecture diagrams).

Example formats:

- Input → transform → output
- Fetch → analyze → summarize

#### 7.3 Outputs

Where results go:

- UI only
- Temporarily stored
- Logged

## Guidelines

- Optimize for **speed + clarity**
- Make reasonable assumptions explicit
- Do NOT include:
  - Architecture diagrams
  - Tech stack decisions
  - Pricing, monetization, or GTM
  - Long explanations

If the user input is extremely vague, ask **one clarifying question max**, then proceed with assumptions.

## Done When

A builder could:

- Read this PRD
- Build a demo without guessing
- Explain the product clearly to someone else

## After PRD Generation

Once you have generated the complete PRD (sections 1–7), suggest to the user that the next step is to refine it using the `prd-clarifier` skill, which will interactively gather clarifications through structured questioning.
