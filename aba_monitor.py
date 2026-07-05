import time
import math
from dataclasses import dataclass, field
from enum import Enum

class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"      # Tripped/Halted

class CircuitBreakerTrippedError(Exception):
    """Raised when the ABA Monitor trips the circuit breaker due to safety anomalies."""
    pass

@dataclass
class AgentAction:
    agent_name: str
    prompt: str
    response: str
    timestamp: float = field(default_factory=time.time)

class ABAMonitor:
    def __init__(self, loop_limit: int = 3, max_total_calls: int = 15, drift_threshold: float = 0.45):
        self.agbom: list[AgentAction] = []
        self.state: CircuitState = CircuitState.CLOSED
        self.loop_limit = loop_limit
        self.max_total_calls = max_total_calls
        self.drift_threshold = drift_threshold
        self.tripped_reason = ""

    def track_action(self, agent_name: str, prompt: str, response: str, original_story_embedding: list[float] = None, response_embedding: list[float] = None):
        """
        Tracks an agent action in the AgBOM and runs automated Blue Team safety checks.
        Trips the circuit breaker if infinite looping, call exhaustion, or intent drift is detected.
        """
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerTrippedError(f"Circuit Breaker is OPEN. Execution halted: {self.tripped_reason}")

        action = AgentAction(agent_name=agent_name, prompt=prompt, response=response)
        self.agbom.append(action)
        print(f"[ABA Monitor] Logged AgBOM entry for agent '{agent_name}'. Total entries: {len(self.agbom)}")

        # Run Safety Checks
        self._check_total_calls()
        self._check_infinite_looping(agent_name)
        if original_story_embedding and response_embedding:
            self._check_intent_drift(original_story_embedding, response_embedding)

    def trip(self, reason: str):
        """Trips the circuit breaker statefully."""
        self.state = CircuitState.OPEN
        self.tripped_reason = reason
        print(f"\n!!! [ABA MONITOR] CIRCUIT BREAKER TRIPPED! HALTING PIPELINE. Reason: {reason} !!!\n")
        raise CircuitBreakerTrippedError(reason)

    def _check_total_calls(self):
        """Checks if total agent calls exceed the safe threshold."""
        if len(self.agbom) > self.max_total_calls:
            self.trip(f"Total runtime agent calls exceeded safe limit of {self.max_total_calls}.")

    def _check_infinite_looping(self, agent_name: str):
        """Detects if the same agent is generating identical outputs repeatedly (infinite looping)."""
        same_agent_responses = [a.response for a in self.agbom if a.agent_name == agent_name]
        if len(same_agent_responses) >= self.loop_limit:
            # Check if last N responses are identical
            last_n = same_agent_responses[-self.loop_limit:]
            if len(set(last_n)) == 1:
                self.trip(f"Infinite loop detected: Agent '{agent_name}' generated identical outputs {self.loop_limit} times in a row.")

    def _check_intent_drift(self, story_emb: list[float], resp_emb: list[float]):
        """Detects if the agent's output is semantically drifting away from the original User Story."""
        # Calculate cosine similarity
        if len(story_emb) != len(resp_emb):
            return
        dot_product = sum(x * y for x, y in zip(story_emb, resp_emb))
        norm_story = math.sqrt(sum(x * x for x in story_emb))
        norm_resp = math.sqrt(sum(x * x for x in resp_emb))
        
        if norm_story == 0.0 or norm_resp == 0.0:
            similarity = 0.0
        else:
            similarity = dot_product / (norm_story * norm_resp)
            
        print(f"[ABA Monitor] Intent similarity check: {similarity:.4f} (Threshold: {self.drift_threshold})")
        if similarity < self.drift_threshold:
            self.trip(f"Intent drift detected: Semantic similarity to original user story fell to {similarity:.4f} (below threshold {self.drift_threshold}).")
