import anthropic
import os
import subprocess
import tempfile
import json

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Maximum iterations before giving up
MAX_ITERATIONS = 5

def execute_code(code: str, timeout: int = 30) -> dict:
    """
    Execute Python code in an isolated Docker container.
    
    Uses python:3.11-slim image — no access to host filesystem,
    network, or environment variables. Safe to run untrusted code.
    
    Args:
        code: Python code string to execute
        timeout: Maximum seconds before killing the container
        
    Returns:
        dict with stdout, stderr, exit_code, and success flag
    """
    try:
        result = subprocess.run(
            [
                "docker", "run",
                "--rm",                          # remove container after exit
                "--network", "none",             # no network access
                "--memory", "128m",              # memory limit
                "--cpus", "0.5",                 # CPU limit
                "python:3.11-slim",
                "python", "-c", code
            ],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exit_code": result.returncode,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds",
            "exit_code": -1,
            "success": False
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "success": False
        }

# Tool definition sent to the Claude API
TOOLS = [
    {
        "name": "execute_code",
        "description": """Execute Python code and return the output.
Use this to test your solution before presenting it.
The environment has Python 3.11 with standard library only — no pip installs.
Always print your results explicitly.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "explanation": {
                    "type": "string", 
                    "description": "Brief explanation of what this code does"
                }
            },
            "required": ["code", "explanation"]
        }
    }
]

SYSTEM_PROMPT = """You are an expert Python engineer who writes and tests code iteratively.

Your workflow:
1. Understand the task
2. Write Python code to solve it
3. Execute the code using the execute_code tool
4. If there are errors, fix them and try again
5. Once the code works correctly, explain the solution

Rules:
- Always test your code before presenting it as a solution
- If execution fails, read the error carefully and fix the specific issue
- Use print() to show results — the sandbox captures stdout
- Only standard library is available (no numpy, pandas, etc.)
- Keep code clean and well-commented
- Maximum 5 attempts before explaining why it cannot be solved"""

def run_agent(task: str) -> None:
    """
    Run the code execution agent on a given task.
    Implements the agentic loop with tool use.
    """
    print(f"\nTask: {task}")
    print("=" * 60)
    
    messages = [{"role": "user", "content": task}]
    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Add assistant response to history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "text" and block.text:
                    print(f"\nAgent: {block.text}")

                elif block.type == "tool_use":
                    tool_input = block.input
                    code = tool_input.get("code", "")
                    explanation = tool_input.get("explanation", "")

                    print(f"\n[Attempt {iteration}] {explanation}")
                    print(f"Code:\n{code}")

                    # Execute in Docker sandbox
                    result = execute_code(code)

                    if result["success"]:
                        print(f"Output: {result['stdout']}")
                    else:
                        print(f"Error: {result['stderr']}")

                    # Return result to agent
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })

            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            # Agent finished — extract final text response
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    print(f"\nFinal Answer:\n{block.text}")
            break

    if iteration >= MAX_ITERATIONS:
        print(f"\nMax iterations ({MAX_ITERATIONS}) reached.")

if __name__ == "__main__":
    # Test with progressively complex tasks
    tasks = [
        "Write a function that finds all prime numbers up to N using the Sieve of Eratosthenes. Test it with N=50.",
        "Write a function that parses a CSV string and returns the column averages. Test with sample data.",
        "Implement a simple LRU cache class with get and put methods. Demonstrate with 5 operations.",
    ]

    for task in tasks:
        run_agent(task)
        print("\n" + "─" * 60)