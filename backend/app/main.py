from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__, nodes  # noqa: F401  (registers node types)
from .api.routes import router, run_stream
from .config import DB_PATH, FRONTEND_DIST, ensure_dirs, load_settings
from .hotkeys import HotkeyManager
from .run_manager import RunHub, RunManager
from .seed import seed
from .services import Services
from .sessions import RealtimeSession, TrackerSession
from .storage import Database


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    db = Database(DB_PATH)
    db.recover_stale_runs()
    seed(db)
    services = Services(db)
    hub = RunHub()
    runs = RunManager(db, services, hub)
    app.state.db = db
    app.state.services = services
    app.state.hub = hub
    app.state.runs = runs
    app.state.realtime = RealtimeSession(services)
    app.state.tracker = TrackerSession(services)
    hotkeys = HotkeyManager()
    app.state.hotkeys = hotkeys
    settings = load_settings(db)
    hotkey_config = settings.get("hotkeys", {})
    if hotkey_config.get("enabled"):
        def on_hotkey(action: str) -> None:
            if action == "start":
                app.state.realtime.start()
            elif action == "stop":
                app.state.realtime.stop()
            elif action == "tracker":
                if app.state.tracker.status()["running"]:
                    app.state.tracker.stop()
                else:
                    app.state.tracker.start()

        hotkeys.start(
            {
                "start": str(hotkey_config.get("start") or "f9"),
                "stop": str(hotkey_config.get("stop") or "f10"),
                "tracker": str(hotkey_config.get("tracker") or "f11"),
            },
            on_hotkey,
        )
    yield
    try:
        hotkeys.stop()
        app.state.realtime.stop()
        app.state.tracker.stop()
    except Exception:
        pass


app = FastAPI(
    title="Rocogi 洛克工坊",
    version=__version__,
    description="洛克王国：世界 本地优先自动化工作台",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/api")
def api_root():
    return {"name": "Rocogi", "version": __version__, "docs": "/docs"}


@app.websocket("/api/ws/runs/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str):
    await run_stream(websocket, run_id)


class SPAStaticFiles(StaticFiles):
    """Serve the Vue SPA and fall back to index.html for client-side routes."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api"):
                return await super().get_response("index.html", scope)
            raise


if FRONTEND_DIST.exists():
    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
