import os, yaml
from graph.compiler import GraphCompiler, CompiledGraph
import asyncio

with open("config.yml") as f: config = yaml.safe_load(f)

# os.environ["LANGSMITH_TRACING"] = "true"
# os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
# os.environ["LANGSMITH_API_KEY"] = config["langsmith"]["key"]
# os.environ["LANGSMITH_PROJECT"] = "homelab-agent"

# graph_constructor: CompiledGraph = asyncio.run(GraphCompiler(checkpoint="langsmith"))
# graph = graph_constructor.graph
