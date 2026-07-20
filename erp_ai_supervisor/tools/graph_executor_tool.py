# tools/graph_executor_tool.py

from langchain.tools import tool
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")   # Headless backend (no GUI)
import matplotlib.pyplot as plt
import ast
import threading
import os
import uuid
import subprocess  # ⭐ NEW (for subprocess sandbox)
import json        # ⭐ NEW
import sys  # ⭐ NEW
import shlex  # ⭐ NEW for Windows safe quoting




# --------------------------------------------------------------
# 1. STATIC CODE SAFETY CHECK USING AST
# --------------------------------------------------------------
def is_code_safe(code: str) -> (bool, str):
    """
    Rejects malicious Python code by scanning AST.
    Blocks:
    - imports (EXCEPT numpy)
    - exec/eval
    - file access
    - attribute hacks
    - OS/system operations
    """

    banned_nodes = (
        ast.With,
        ast.Try,
        ast.Raise,
        ast.AsyncFunctionDef,
    )

    banned_names = {
        "exec", "eval", "__import__", "open", "compile",
        "os", "sys", "subprocess", "shutil", "pathlib",
        "input", "globals", "locals",
    }

    try:
        tree = ast.parse(code)
    except Exception as e:
        return False, f"Syntax error in code: {str(e)}"

    for node in ast.walk(tree):

        # 1. Block banned AST node types (but allow Import/ImportFrom for safe libs)
        if isinstance(node, banned_nodes):
            return False, f"Blocked dangerous Python construct: {type(node).__name__}"

        # 2. Check imports - ALLOW only numpy, matplotlib, pandas and their submodules
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not any(alias.name.startswith(mod) for mod in ("numpy", "matplotlib", "pandas")):
                    return False, f"Blocked import: {alias.name}"
        
        if isinstance(node, ast.ImportFrom):
            if node.module and not any(node.module.startswith(mod) for mod in ("numpy", "matplotlib", "pandas")):
                return False, f"Blocked import from: {node.module}"

        # 3. Block dangerous variable/function names
        if isinstance(node, ast.Name) and node.id in banned_names:
            return False, f"Blocked unsafe name: {node.id}"

        # 4. Block attribute access like object.__class__, object.__dict__
        if isinstance(node, ast.Attribute):
            if "__" in node.attr:
                return False, f"Blocked attribute access: {node.attr}"

    return True, "safe"


# --------------------------------------------------------------
# 2. Build restricted sandbox
# --------------------------------------------------------------
def build_sandbox(df: pd.DataFrame):
    """
    Creates a restricted environment allowing only:
    - matplotlib.pyplot as plt
    - numpy as np (for array operations in grouped bars)
    - pandas DataFrame df
    """

    safe_globals = {
        "plt": plt,
        "np": np,
        "df": df,
        "__builtins__": {
            "float": float,
            "int": int,
            "str": str,
            "len": len,
            "range": range,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
        }
    }

    safe_locals = {}

    return safe_globals, safe_locals


# --------------------------------------------------------------
# 3. Windows-safe timeout using THREADS
# --------------------------------------------------------------
def run_with_timeout(func, args=(), timeout=2):

    result = {"error": None}

    def wrapper():
        try:
            func(*args)
        except Exception as e:
            result["error"] = str(e)

    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()

    thread.join(timeout)

    if thread.is_alive():
        return "TIMEOUT"

    return result["error"]


# --------------------------------------------------------------
# 4. DATA CLEANING BEFORE EXECUTION
# --------------------------------------------------------------
def clean_dataframe(df: pd.DataFrame):
    """
    Ensures DataFrame is safe and numeric for plotting.
    """

    df = df.dropna(how="all", axis=1)

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="ignore")

    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"])

    if df.empty:
        return None 

    return df


# --------------------------------------------------------------
#  NEW SUBPROCESS RUNNER FILE CREATION
# --------------------------------------------------------------
def write_subprocess_runner(df: pd.DataFrame, code: str, script_path: str):
    """
    Writes a temporary Python script that:
    - loads the dataframe
    - executes ONLY the user's matplotlib code
    """

    # Write DataFrame to a separate JSON file to avoid escaping issues
    json_path = script_path.replace(".py", ".json")
    df.to_json(json_path)

    #  CHANGE 1 — clean_code removes plt.show()
    clean_code = code.replace("plt.show()", "")

    # Use json_path as a string in the runner script
    runner_code = f"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_json(r'{json_path}')

{clean_code}

plt.savefig(r"{script_path.replace(".py", ".png")}", bbox_inches="tight")
"""

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(runner_code)


# --------------------------------------------------------------
# 5. LangChain Tool: graph_executor
# --------------------------------------------------------------
@tool("graph_executor")
def graph_executor(code: str, dataframe: dict):
    """
    Executes matplotlib code safely using a sandbox and timeout.
    Returns a dict with:
      - image_path: path to the saved PNG file (inside generated_graphs/)
      - or error: error message
    """

    try:
        df = pd.DataFrame(dataframe)
    except Exception as e:
        return {"error": f"Failed to construct DataFrame: {str(e)}"}

    df = clean_dataframe(df)
    if df is None or df.empty:
        return {"error": "No data available for plotting."}

    # Allow both numeric and string columns for plotting
    # (Bills Receivable with only strings can be counted/grouped)
    # Only check that we have at least some data
    if df.empty:
        return {"error": "DataFrame is empty."}

    code = code.replace("plt.show()", "")

    is_safe, msg = is_code_safe(code)
    if not is_safe:
        return {"error": msg}

    # ----------------------------------------------------------
    # REPLACEMENT: EXECUTE CODE IN SUBPROCESS INSTEAD OF exec()
    # ----------------------------------------------------------
    os.makedirs("generated_graphs", exist_ok=True)

    temp_script = f"generated_graphs/tmp_{uuid.uuid4().hex}.py"
    temp_image = temp_script.replace(".py", ".png")

    write_subprocess_runner(df, code, temp_script)

    safe_script = shlex.quote(os.path.abspath(temp_script))

    try:
        result = subprocess.run(
            f'"{sys.executable}" {temp_script}',
            shell=True,
            capture_output=True,
            text=True,
            timeout=5   #  CHANGE 2 — timeout increased from 2 → 5
        )
    except subprocess.TimeoutExpired:
        return {"error": "Subprocess timed out"}

    if result.returncode != 0:
        return {"error": f"Subprocess failed: {result.stderr}"}

    if not os.path.exists(temp_image):
        return {"error": "Graph image not generated by subprocess"}

    final_filename = f"graph_{uuid.uuid4().hex}.png"
    final_path = os.path.join("generated_graphs", final_filename)
    os.rename(temp_image, final_path)

    # Clean up temporary files (script, JSON, and image)
    json_path = temp_script.replace(".py", ".json")
    if os.path.exists(temp_script):
        os.remove(temp_script)
    if os.path.exists(json_path):
        os.remove(json_path)

    return {"image_path": final_path}
