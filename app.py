"""Flask server entry point.  Run with:  python app.py

Keep this file's top-level imports light. On Windows, every worker process
re-imports the file that launched it, so heavy imports here would be paid
by each worker and inflate the measured times. Everything is imported
inside main() instead.
"""


def main():
    from api import config
    from api.routes import create_app

    app = create_app()
    print(f"Open http://{config.HOST}:{config.PORT} in your browser")
    # debug and the reloader stay off: the reloader restarts the process and
    # conflicts with multiprocessing.
    app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":  # required on Windows for multiprocessing
    main()