from pydantic import BaseModel, ConfigDict


class HintRequest(BaseModel):
    code: str
    problem_description: str
    programming_language: str
    difficulty: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "def twoSum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]",
                "problem_description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
                "programming_language": "python",
                "difficulty": "Easy"
            }
        }
    )


class HintResponse(BaseModel):
    thought_process: str
    hint: str
    conceptual_explanation: str | None = None
    pseudocode_steps: list[str] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "thought_process": "The user is using a brute-force O(n^2) solution. I will suggest a hash map approach to improve it to O(n) time complexity.",
                "hint": "Try storing each number's index in a hash map as you iterate. Can you look up the complement (target - num) in constant time?",
                "conceptual_explanation": "A hash map provides O(1) average lookup time. By storing seen numbers, we can find the matching pair in a single pass instead of nested loops.",
                "pseudocode_steps": None
            }
        }
    )


class SessionMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class Session(BaseModel):
    session_id: str
    history: list[SessionMessage]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session_9823f",
                "history": [
                    {"role": "user", "content": "I am stuck on Two Sum. How do I optimize the nested loops?"},
                    {"role": "assistant", "content": "Think about how a hash map can help you find seen values quickly."}
                ]
            }
        }
    )
