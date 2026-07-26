"""ReAct agent loop — the core of the AI coding agent framework."""

import logging
from typing import Callable, List, Optional

from ..config import config
from ..llm.base import BaseProvider, LLMResponse, ToolResult
from ..prompts.system import build_system_prompt
from .memory import Memory
from .planner import Planner
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class Agent:
    """A ReAct-pattern AI coding agent.

    The agent loop:
    1. Plan — generate a step-by-step plan for the task
    2. Act — ask the LLM what to do next (with tool access)
    3. Observe — execute tool calls and feed results back
    4. Repeat until the task is complete or max iterations reached
    """

    def __init__(
        self,
        task: str,
        provider: BaseProvider,
        tool_registry: ToolRegistry,
        on_thinking: Optional[Callable[[str], None]] = None,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
    ):
        self._task = task
        self._provider = provider
        self._tools = tool_registry
        self._memory = Memory()
        self._planner = Planner(provider)
        self._on_thinking = on_thinking
        self._on_tool_call = on_tool_call
        self._iteration = 0
        self._is_complete = False

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    def run(self) -> str:
        """Execute the agent loop until completion or max iterations.

        Returns:
            The final summary/output string.
        """
        logger.info(f"Agent starting task: {self._task}")

        # Set up system prompt with tool schemas
        tool_schemas = self._tools.get_schemas()
        system_content = build_system_prompt(
            task=self._task,
            workspace=str(config.workspace),
            tools=self._tools.list_tools(),
        )
        self._memory.add_system(system_content)

        # Phase 1: Planning
        self._emit_thinking("Planning...")
        steps = self._planner.plan(self._task)
        plan_text = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(steps))
        self._emit_thinking(f"Plan:\n{plan_text}")

        # Add the task with the plan
        self._memory.add_user(
            f"Task: {self._task}\n\nPlan (follow these steps):\n{plan_text}\n\n"
            f"Current workspace: {config.workspace}\n"
            f"Start by executing step 1."
        )

        # Phase 2: ReAct loop
        while self._iteration < config.max_iterations:
            self._iteration += 1
            logger.info(f"Iteration {self._iteration}/{config.max_iterations}")

            # Get LLM response
            response = self._provider.chat(
                messages=self._memory.get_history(),
                tools=tool_schemas,
            )

            # Handle text content
            if response.content:
                self._emit_thinking(response.content)
                self._memory.add_assistant(response.content, response.tool_calls)

            # Check for completion signal
            if self._check_completion(response):
                self._is_complete = True
                return response.content or "Task completed."

            # Execute tool calls
            if response.has_tool_calls:
                tool_results = self._execute_tools(response)
                self._memory.add_tool_results(tool_results)
            else:
                # No tool calls and no completion — agent may be done
                if response.content and not response.has_tool_calls:
                    self._emit_thinking("Agent has no more actions. Finishing.")
                    self._is_complete = True
                    return response.content or "Task completed."

        logger.warning(f"Agent reached max iterations ({config.max_iterations})")
        return f"Task reached maximum iterations ({config.max_iterations}). Partial results above."

    def _execute_tools(self, response: LLMResponse) -> List[ToolResult]:
        """Execute all tool calls in the response and return results."""
        results = []
        for tc in response.tool_calls:
            self._emit_tool_exec(tc.name, tc.arguments)
            logger.info(f"Executing tool: {tc.name}({tc.arguments})")

            result_text = self._tools.execute(tc.name, tc.arguments)
            results.append(ToolResult(
                tool_call_id=tc.id,
                name=tc.name,
                result=result_text,
            ))

            # Log truncated result
            preview = result_text[:200] + "..." if len(result_text) > 200 else result_text
            logger.info(f"Tool result: {preview}")

        return results

    def _check_completion(self, response: LLMResponse) -> bool:
        """Check if the agent is signaling task completion."""
        if not response.content:
            return False

        lower = response.content.lower()
        completion_phrases = [
            "task complete", "task is complete", "done with the task",
            "finished the task", "all steps complete", "i have completed",
        ]
        return any(phrase in lower for phrase in completion_phrases)

    def _emit_thinking(self, text: str) -> None:
        if self._on_thinking:
            self._on_thinking(text)

    def _emit_tool_exec(self, name: str, args: dict) -> None:
        if self._on_tool_call:
            self._on_tool_call(name, args)
