import sys
import os

# Add q3 directory to path
q3_path = os.path.join(os.path.dirname(__file__), 'q3')
sys.path.insert(0, q3_path)

# Change working directory to q3 for static files and templates
os.chdir(q3_path)

# Import the app from q3's main module
import importlib.util
spec = importlib.util.spec_from_file_location("q3_main", os.path.join(q3_path, "main.py"))
if spec is None or spec.loader is None:
    raise ImportError("Could not load q3 main module")
q3_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q3_main)

# Get the app instance
app = q3_main.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 