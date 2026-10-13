import os
import sys
import uvicorn


def main():
    if "--gradio" in sys.argv:
        from modules.ui.gradio_app import launch_demo
        launch_demo()
        return

    port = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", "7860")))
    host = os.getenv("HOST", os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"))

    print("\n" + "=" * 62)
    print("  TMed-QA - Medical AI Agentic CRAG Web Application")
    print(f"  Access UI at: http://{host}:{port}")
    print("=" * 62 + "\n")

    uvicorn.run("modules.ui.web_server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()