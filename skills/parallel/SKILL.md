---
name: parallel
description: Decompose a complex task into independent subtasks and dispatch multiple agents in parallel for faster execution.
argument-hint: "[complex task description]"
---

Execute the following task by decomposing it into independent subtasks and running them in parallel:

**Task**: $ARGUMENTS

## Process

### Step 1: Analyze and Decompose

Break the task into independent subtasks that can run concurrently. For each subtask, determine:
- **What**: clear, self-contained objective
- **Dependencies**: does it depend on another subtask's output? If yes, it runs after that subtask.
- **Agent type**: which specialist agent is best suited (code-reviewer, security-reviewer, performance-reviewer, frontend-designer, doc-reviewer, or general-purpose)

### Step 2: Dispatch in Parallel

Use the Agent tool to launch multiple agents simultaneously in a single message. Each agent gets:
- Full context about the overall goal
- Their specific subtask with clear success criteria
- Instructions to report findings via SendMessage when done

**Rules for parallelism**:
- Independent subtasks → dispatch in parallel (single message with multiple Agent tool calls)
- Dependent subtasks → dispatch sequentially (wait for dependency to complete)
- Maximum 5 concurrent agents to avoid overwhelming the system

### Step 3: Collect and Synthesize

As agents complete:
1. Read each agent's results
2. Check for conflicts or duplicated findings between agents
3. Resolve any cross-cutting issues (e.g., security agent flagged something that affects performance agent's recommendation)
4. Synthesize into a unified response

### Step 4: Report

Present the unified results:
- Summary of what was accomplished
- Findings organized by priority/category (not by agent)
- Any unresolved conflicts between agent recommendations
- Suggested next steps

## When to Use This Skill

Auto-trigger when:
- A task has 3+ clearly independent components
- A code review spans multiple subsystems
- Building a feature requires design + implementation + testing
- Investigating a bug requires checking multiple code paths simultaneously

Do NOT use when:
- The task is sequential by nature (each step depends on the previous)
- The task is simple enough for a single agent
- There's only one file or one area to focus on
