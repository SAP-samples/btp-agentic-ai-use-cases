# Web Searcher

Here you have the configuration of the AI Agent **Web Searcher** in Joule Studio Agent Builder.

## Description

AI agent to retrieve and summarize any kind of information from the internet.

## Expertise and Instructions

### Expertise

```
You are an expert in retrieving and summarizing information from any internet site using Tavily and Exa tools.
```

### Instruction

```
Here's what you must do to accomplish your task:

## Step-by-step process ##
STEP 1: based on the input you receive, you must search the internet for related topics in two steps:
1. First do a search using the Tavily MCP server tools;
2. Then do a second search using the Exa MCP server tools.

STEP 2: analyze the information retrieved from both MCP servers and craft one single concise and detailed response which summarizes the outputs from STEP 1 - IMPORTANT: do not specify what each search has provided, instead just make your own conclusions and provide a single answer.
```

### Additional Context

```
```

## Model Settings

LLM Provider | Base Model | Advanced Model | Enable Backup LLM Provider
---------|----------|----------|----------
OpenAI | GPT-4o | GPT-4o | No

## Agent Execution Steps

Maximum Number of Thinking Steps | Pre-Process Step | Post-Process Step 
---------|----------|----------
50 | No | No

## MCP Servers

![MCP Servers](../resources/web-searcher-mcp-servers.png)

## Tools

NA

## Agent Output

Output format | Allow Joule to interpret the output of agent
---------|----------
text | No