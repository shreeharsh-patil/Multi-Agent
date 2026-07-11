"""Check Google ADK capabilities"""
import google.adk as adk

print("=== ADK Version ===")
print(adk.__version__)

print("\n=== Agent class ===")
print(type(adk.Agent))
sig = dir(adk.Agent)
print([s for s in sig if not s.startswith('_')])

print("\n=== Runner ===")
print(type(adk.Runner))
print([s for s in dir(adk.Runner) if not s.startswith('_')])

print("\n=== Event ===")
print(type(adk.Event))
print([s for s in dir(adk.Event) if not s.startswith('_')])

print("\n=== Context ===")
print(type(adk.Context))
print([s for s in dir(adk.Context) if not s.startswith('_')])

print("\n=== Workflow ===")
print(type(adk.Workflow))
print([s for s in dir(adk.Workflow) if not s.startswith('_')])

print("\n=== tools ===")
print([s for s in dir(adk.tools) if not s.startswith('_')])

print("\n=== models ===")
print([s for s in dir(adk.models) if not s.startswith('_')])

print("\n=== agents submodules ===")
print([s for s in dir(adk.agents) if not s.startswith('_')])

print("\n=== Runner init signature ===")
import inspect
try:
    print(inspect.signature(adk.Runner.__init__))
except:
    print("Could not inspect")

print("\n=== Agent init signature ===")
try:
    print(inspect.signature(adk.Agent.__init__))
except:
    print("Could not inspect")
