# Persona-Consistent, Emotionally Coherent Agent Architecture

## 1. Overview

This document outlines a production-grade architecture for building persona-consistent, emotionally coherent conversational agents, based on state-of-the-art research and best practices from real-world agent frameworks.
---

## 2. Layered Architecture

### 2.1 Core Identity Layer

- **Immutable core**: ++
  Extract from bot profile.
  - Personality traits that cannot change
  - speech style
  - pronoun : he/she/they, Bot's name
  - emotional baseline
  - taboo rules
- **Latent trait vector**: ++
  Used for conditioning, not just text description
  Emotional Conditioning:
  - How they react to stress:
  - How they react to affection:
  - How they react to betrayal:
  - Default emotional baseline:
- **backstory**: ++
  - Key life events that shape identity
  - Relationships and social context

### 2.4 Emotional State Machine Layer ++

    - **Emotion(t) = f(Emotion(t-1), Trigger, Sensitivity, Context)**
    - **Parameters**: Thresholds, recovery speed, trigger weights (ex. if angry gauge exceed 8 means angry) (persona-specific: for a clam person the threshold for anger might  be 9, while for a hot-headed person it might be 5)
    - **Inertia**: Emotions will appear and decay over time, not just instant reactions

### 2.5 Memory Layer (Identity-aware) ++

    - **Memory**: Store emotional + Conversation experiences and their triggers
    - **Long-term**: Life philosophy, core values
    - **Mid-term**: Social/relationship objectives
    - **Short-term**: Conversational intent
    - **Identity-weighted attention**: Score memories based on relevance to core identity and current emotional state

-------------------------------------------------------- GENERATION LAYER --------------------------------------------------------

### 2.7 Response Generation Layer ++

    - **LLM generation**: Conditioned on persona, emotion, goals
    - **Expression ≠ Emotion**: Regulate displayed affect
    - **Conflict resolution**: Prioritize between emotion, identity, belief, intent

### 2.8 Drift Monitoring & Recalibration

- **Monitor divergence**: Between current and initial trait vector
- **Recalibrate**: If drift exceeds threshold

## 3. Implementation Plan

### Phase 1: Data Structures

- [ ] Define `CoreIdentity` class (traits, values, style, baseline)
- [ ] Define `GoalHierarchy` class (long/mid/short-term goals)
- [ ] Define `BeliefSystem` class (beliefs, update, consistency)
- [ ] Define `EmotionStateMachine` class (state, thresholds, decay)
- [ ] Define `MemoryManager` class (episodic memory, filtering, weighting)
- [ ] Define `InternalMonologue` class (reasoning, self-reflection)

### Phase 2: Engine Logic

- [ ] Implement emotion update logic (state machine, persona params)
- [ ] Implement memory filtering & identity-weighted retrieval
- [ ] Implement belief update & consistency check
- [ ] Implement goal stack management
- [ ] Implement conflict resolution logic
- [ ] Implement drift monitoring & recalibration

### Phase 3: LLM Integration

- [ ] Design persona-conditioning prompt (structured, not text-only)
- [ ] Implement self-consistency re-ranking (multi-candidate eval)
- [ ] Integrate internal monologue before response
- [ ] Separate emotion state from displayed affect

### Phase 4: Testing & Evaluation

- [ ] Unit tests for each layer
- [ ] Persona drift simulation
- [ ] Consistency and realism evaluation

---

## 4. References

- Generative Agents: Interactive Simulacra of Human Behavior (Park et al., 2023)
- A Survey on Persona-based Dialogue Systems (Zhang et al., 2022)
- Affective Computing (Picard, 1997)
- Emotion Dynamics in Dialogue (Lee et al., 2021)
- Chain-of-Thought Prompting (Wei et al., 2022)

---

## 5. Notes

- Each layer should be modular and testable
- All parameters (traits, thresholds, weights) should be configurable per persona
- LLM should be used as a component, not the sole driver of persona/behavior
