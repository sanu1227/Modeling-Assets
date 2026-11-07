"""Run in the full Unreal Editor with /Game/CrateLab/CratePreview open.

Use -ExecutePythonScript, not the -run=pythonscript commandlet: SIE needs editor
ticks and a viewport. The map is never saved. Only a temporary, unsaved test actor is
added, and it is removed after the simulation. Results go to ../logs/.
"""
import hashlib
import json
import math
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "UnrealCrate"
MAP = PROJECT / "Content" / "CrateLab" / "CratePreview.umap"
LEVEL = "/Game/CrateLab/CratePreview"
REPORT = ROOT / "logs" / "unreal_crate_runtime_validation.json"
SCREENSHOT = ROOT / "logs" / "unreal_crate_preview.png"
TAG = "CrateRuntimeDropTest"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
report = {"passed": False, "status": "running", "mode": "SIE",
          "started_utc": datetime.now(timezone.utc).isoformat(), "samples": []}


def write_report():
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def evaluate_samples(samples, floor_top):
    last = samples[-1]
    settled = [sample for sample in samples if sample["time_s"] >= last["time_s"] - 0.5]
    return {
        "simulated_at_least_3_seconds": last["time_s"] >= 3.0,
        "fell_at_least_150_cm": samples[0]["bottom_z_cm"] - last["bottom_z_cm"] >= 150.0,
        "downward_velocity_observed": any(sample["vertical_speed_cm_s"] < -10.0 for sample in samples),
        "resting_on_floor": abs(last["bottom_z_cm"] - floor_top) <= 2.0,
        "stopped": last["speed_cm_s"] <= 3.0,
        "settled_for_half_second": len(settled) >= 2 and
            settled[-1]["time_s"] - settled[0]["time_s"] >= 0.4 and
            max(sample["bottom_z_cm"] for sample in settled) -
            min(sample["bottom_z_cm"] for sample in settled) <= 1.0,
        "no_sample_below_floor": min(sample["bottom_z_cm"] for sample in samples) >= floor_top - 2.0,
    }


def verify():
    test_actor = None
    started_play = False
    before_hash = None
    editor_actor_paths = None
    try:
        project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
        assert project == PROJECT.resolve(), "Open UnrealCrate/CrateLab.uproject first."
        assert not levels.is_in_play_in_editor(), "Stop the existing play session before this test."
        assert editor.get_editor_world().get_path_name().split(".")[0] == LEVEL, "Open CratePreview first."
        assert MAP.is_file(), str(MAP)
        before_hash = hashlib.sha256(MAP.read_bytes()).hexdigest()
        existing = actors.get_all_level_actors()
        editor_actor_paths = {actor.get_path_name() for actor in existing}
        assert not any(actor.actor_has_tag(TAG) for actor in existing), "Previous test actor still exists."
        floor = next(actor for actor in existing if actor.get_actor_label() == "Preview_Floor")
        floor_origin, floor_extent = floor.get_actor_bounds(False)
        floor_top = floor_origin.z + floor_extent.z
        report["floor_top_z_cm"] = floor_top
        mesh = unreal.load_asset("/Game/CrateLab/SM_Crate")
        assert isinstance(mesh, unreal.StaticMesh), "Run setup_unreal_crate.py first."

        test_actor = actors.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(180, 0, floor_top + 220), transient=False)
        assert test_actor is not None
        test_actor.set_actor_label(TAG)
        test_actor.set_editor_property("tags", [TAG])
        component = test_actor.get_component_by_class(unreal.StaticMeshComponent)
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_static_mesh(mesh)
        component.set_collision_profile_name("PhysicsActor")
        component.set_enable_gravity(True)

        started_play = True
        levels.editor_play_simulate()
        deadline = time.monotonic() + 90.0
        while not levels.is_in_play_in_editor() or editor.get_game_world() is None:
            assert time.monotonic() < deadline, "SIE did not start within 90 seconds."
            yield
        world = editor.get_game_world()
        copies = unreal.GameplayStatics.get_all_actors_with_tag(world, TAG)
        assert len(copies) == 1, "The temporary test actor was not duplicated into the SIE world."
        simulated = copies[0]
        assert simulated.get_path_name() != test_actor.get_path_name(), "Must test the SIE copy."
        component = simulated.get_component_by_class(unreal.StaticMeshComponent)
        component.set_simulate_physics(True)
        assert component.is_simulating_physics(), "The crate has no usable simulated rigid body."
        report["runtime_actor"] = simulated.get_path_name()
        start = unreal.GameplayStatics.get_time_seconds(world)
        deadline = time.monotonic() + 90.0
        while True:
            assert levels.is_in_play_in_editor(), "SIE was stopped before the test completed."
            elapsed = unreal.GameplayStatics.get_time_seconds(world) - start
            origin, extent = simulated.get_actor_bounds(False)
            velocity = component.get_physics_linear_velocity()
            report["samples"].append({
                "time_s": elapsed, "bottom_z_cm": origin.z - extent.z,
                "speed_cm_s": math.sqrt(velocity.x ** 2 + velocity.y ** 2 + velocity.z ** 2),
                "vertical_speed_cm_s": velocity.z,
            })
            if elapsed >= 3.0:
                break
            assert time.monotonic() < deadline, "Simulation time did not advance to 3 seconds."
            yield
        report["checks"] = evaluate_samples(report["samples"], floor_top)
        report["physics_passed"] = all(report["checks"].values())
    except Exception:
        report["error"] = traceback.format_exc()
        unreal.log_error(report["error"])
    finally:
        try:
            if started_play:
                levels.editor_request_end_play()
                deadline = time.monotonic() + 20.0
                while levels.is_in_play_in_editor():
                    assert time.monotonic() < deadline, "SIE did not stop; temporary actor cleanup pending."
                    yield
            if test_actor is not None:
                assert actors.destroy_actor(test_actor), "Failed to remove the temporary editor actor."
            report["temporary_actor_removed"] = not any(
                actor.actor_has_tag(TAG) for actor in actors.get_all_level_actors())
            if editor_actor_paths is not None:
                report["editor_actors_preserved"] = editor_actor_paths == {
                    actor.get_path_name() for actor in actors.get_all_level_actors()}
            if before_hash is not None:
                report["map_file_unchanged"] = hashlib.sha256(MAP.read_bytes()).hexdigest() == before_hash
        except Exception:
            report["cleanup_error"] = traceback.format_exc()
            unreal.log_error(report["cleanup_error"])

    # Optional evidence image, taken after stopping SIE and removing its test actor.
    try:
        assert before_hash is not None and not levels.is_in_play_in_editor(), "Preview capture skipped."
        camera = next(actor for actor in actors.get_all_level_actors()
                      if isinstance(actor, unreal.CameraActor) and actor.get_actor_label() == "Preview_Camera")
        old_mtime = SCREENSHOT.stat().st_mtime_ns if SCREENSHOT.exists() else 0
        task = unreal.AutomationLibrary.take_high_res_screenshot(1280, 720, str(SCREENSHOT), camera=camera)
        assert task.is_valid_task(), "The editor rejected the screenshot request."
        deadline = time.monotonic() + 45.0
        while not task.is_task_done():
            assert time.monotonic() < deadline, "Screenshot request timed out."
            yield
        while not SCREENSHOT.exists() or SCREENSHOT.stat().st_mtime_ns <= old_mtime:
            assert time.monotonic() < deadline, "Screenshot file was not written."
            yield
        assert SCREENSHOT.stat().st_size > 1000, "Screenshot file is unexpectedly small."
        report["screenshot"] = str(SCREENSHOT)
        report["screenshot_saved"] = True
    except Exception:
        report["screenshot_saved"] = False
        report["screenshot_error"] = traceback.format_exc()

    report["passed"] = bool(report.get("physics_passed") and
                            report.get("temporary_actor_removed") and
                            report.get("editor_actors_preserved") and
                            report.get("map_file_unchanged") and not report.get("cleanup_error"))
    report["status"] = "complete"
    write_report()
    unreal.log("CRATE_UNREAL_RUNTIME_VALIDATION " + json.dumps(
        {key: value for key, value in report.items() if key != "samples"}))


def tick(_delta_seconds):
    global tick_busy
    if tick_busy:
        return
    tick_busy = True
    try:
        next(verification)
    except StopIteration:
        unreal.unregister_slate_post_tick_callback(tick_handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(previous_keep_alive)
    except Exception:
        report.update(status="failed", passed=False, error=traceback.format_exc())
        write_report()
        unreal.log_error(report["error"])
        unreal.unregister_slate_post_tick_callback(tick_handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(previous_keep_alive)
    finally:
        tick_busy = False


write_report()
previous_keep_alive = unreal.EditorPythonScripting.get_keep_python_script_alive()
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
verification = verify()
tick_busy = False
tick_handle = unreal.register_slate_post_tick_callback(tick)
