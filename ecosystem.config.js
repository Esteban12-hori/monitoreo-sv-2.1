module.exports = {
  apps: [
    {
      name: "monitor-backend",
      script: ".venv/bin/python",
      args: "-m uvicorn src.server.app.main:app --host 0.0.0.0 --port 8000",
      cwd: "./",
      interpreter: "none",
      env: {
        ENV: "production",
        PYTHONPATH: "./"
      }
    }
  ]
};
