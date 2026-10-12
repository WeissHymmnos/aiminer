import multiprocessing

from aiminer.tui import TUIApp

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    manager_ctx = multiprocessing.Manager()
    app = TUIApp(manager_ctx=manager_ctx)
    print("App created successfully")
