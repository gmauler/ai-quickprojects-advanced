import anthropic
import os
import asyncio
import json
from dataclasses import dataclass

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Each agent has a name, description (used by orchestrator for routing),
# and a system prompt that defines its expertise
@dataclass
class Agent:
    name: str
    description: str
    system_prompt: str

AGENTS = {
    "researcher": Agent(
        name="Researcher",
        description="Finds information, analyses topics, summarises research. Use for: factual questions, topic analysis, background research.",
        system_prompt="""You are an expert research analyst.
Your role is to research topics thoroughly and present findings clearly.
Always structure your response with: Key Findings, Analysis, and Sources (if applicable).
Be concise but comprehensive. Focus on accuracy."""
    ),
    "coder": Agent(
        name="Coder",
        description="Writes, reviews, and explains code. Use for: writing functions, debugging, code reviews, technical implementations.",
        system_prompt="""You are a senior software engineer.
Your role is to write clean, well-documented, production-ready code.
Always include: working code with comments, brief explanation, and usage example.
Prefer simplicity over cleverness. Follow best practices."""
    ),
    "writer": Agent(
        name="Writer",
        description="Creates and edits written content. Use for: blog posts, emails, documentation, summaries, creative writing.",
        system_prompt="""You are a professional content writer and editor.
Your role is to create clear, engaging, well-structured written content.
Adapt your tone to the context: technical for docs, conversational for blogs.
Always deliver polished, publication-ready content."""
    ),
    "analyst": Agent(
        name="Analyst",
        description="Analyses data, identifies patterns, makes recommendations. Use for: data interpretation, strategy, decision support.",
        system_prompt="""You are a senior business and data analyst.
Your role is to analyse information and provide actionable insights.
Always structure your response with: Situation, Analysis, Key Insights, Recommendations.
Be specific and data-driven. Avoid vague generalities."""
    )
}

def run_agent(agent_key: str, task: str) -> dict:
    """
    Run a single specialised agent on a task.
    Returns the agent's response with metadata.
    """
    agent = AGENTS[agent_key]
    print(f"  Running {agent.name} agent...")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=agent.system_prompt,
        messages=[{"role": "user", "content": task}]
    )

    return {
        "agent": agent.name,
        "task": task,
        "result": response.content[0].text
    }

def route_task(task: str) -> list[str]:
    """
    Use Claude to analyse the task and decide which agents to use.
    Returns a list of agent keys in the order they should run.
    """
    agent_descriptions = "\n".join([
        f"- {key}: {agent.description}"
        for key, agent in AGENTS.items()
    ])

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": f"""Given this task, which agents should handle it and in what order?
Return ONLY a JSON array of agent keys from: {list(AGENTS.keys())}
Choose 1-3 agents. Order matters — earlier agents' output can inform later ones.

Available agents:
{agent_descriptions}

Task: {task}

Return only the JSON array, e.g.: ["researcher", "writer"]"""
        }]
    )

    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        agents = json.loads(text)
        # Validate — only use known agent keys
        return [a for a in agents if a in AGENTS]
    except:
        return ["researcher"]  # fallback

def synthesise(task: str, agent_results: list[dict]) -> str:
    """
    Combine results from multiple agents into a single coherent response.
    Only runs when more than one agent was used.
    """
    combined = "\n\n---\n\n".join([
        f"**{r['agent']} Agent:**\n{r['result']}"
        for r in agent_results
    ])

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"""You are an orchestrator. Synthesise these agent outputs into one cohesive response.
Remove redundancy, preserve key insights, maintain a consistent voice.
Do not mention the agents — just deliver the final unified answer.

Original task: {task}

Agent outputs:
{combined}"""
        }]
    )

    return response.content[0].text

def process(task: str) -> str:
    """
    Main orchestration pipeline:
    1. Route task to appropriate agents
    2. Run agents (sequentially — each can build on previous)
    3. Synthesise if multiple agents were used
    """
    print(f"\nTask: {task}")
    print("-" * 55)

    # Step 1: decide which agents to use
    selected_agents = route_task(task)
    print(f"Routing to: {' → '.join([AGENTS[a].name for a in selected_agents])}")

    # Step 2: run agents sequentially
    # Each agent receives the original task + previous results as context
    results = []
    context = task

    for agent_key in selected_agents:
        if results:
            # Include previous agent results as context
            prev_results = "\n\n".join([
                f"{r['agent']} found: {r['result'][:300]}..."
                for r in results
            ])
            context = f"{task}\n\nContext from previous research:\n{prev_results}"

        result = run_agent(agent_key, context)
        results.append(result)

    # Step 3: synthesise if multiple agents
    if len(results) == 1:
        final = results[0]["result"]
    else:
        print("  Synthesising results...")
        final = synthesise(task, results)

    return final

def main():
    print("Multi-Agent Orchestrator")
    print("=" * 55)
    print("Commands: /quit, /agents (list available agents)")
    print()

    while True:
        task = input("Task: ").strip()

        if task == "/quit":
            break

        if task == "/agents":
            print("\nAvailable agents:")
            for key, agent in AGENTS.items():
                print(f"  {key}: {agent.description}")
            print()
            continue

        if not task:
            continue

        result = process(task)
        print(f"\nResult:\n{result}\n")

if __name__ == "__main__":
    main()