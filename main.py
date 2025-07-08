import sys
import os

# Add q3 directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'q3'))

# Import the app from q3
from main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 