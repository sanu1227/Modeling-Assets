"""Run inside the new UnrealCrate/CrateLab.uproject editor.

UnrealEditor.exe CrateLab.uproject -ExecutePythonScript=".../setup_unreal_crate.py"
Re-running updates this script's assets in /Game/CrateLab and tagged actors only.
Other projects, maps, and user-created actors are preserved.
Official APIs: dev.epicgames.com/documentation/en-us/unreal-engine/python-api/
"""
import json
import traceback
from pathlib import Path

import unreal


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "UnrealCrate"
SOURCE = ROOT / "assets" / "Crate"
REPORT = ROOT / "logs" / "unreal_crate_validation.json"
CONTENT = "/Game/CrateLab"
LEVEL = CONTENT + "/CratePreview"
TAG = "CrateLabGenerated"
assets = unreal.AssetToolsHelpers.get_asset_tools()
materials = unreal.MaterialEditingLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
report = {"passed": False, "content_folder": CONTENT, "level": LEVEL}


def set_properties(obj, **values):
    for name, value in values.items():
        obj.set_editor_property(name, value)


def import_asset(filename, name, expected_type, options=None, factory=None):
    task = unreal.AssetImportTask()
    set_properties(task, filename=str(filename), destination_path=CONTENT,
                   destination_name=name, automated=True, async_=False,
                   replace_existing=True, replace_existing_settings=True, save=True)
    if options is not None:
        task.set_editor_property("options", options)
    if factory is not None:
        task.set_editor_property("factory", factory)
    assets.import_asset_tasks([task])
    imported = [obj for obj in task.get_objects() if isinstance(obj, expected_type)]
    assert len(imported) == 1, (filename.name, list(task.imported_object_paths))
    return imported[0]


def material(name):
    result = unreal.load_asset(CONTENT + "/" + name)
    if result is None:
        result = assets.create_asset(name, CONTENT, unreal.Material, unreal.MaterialFactoryNew())
    assert result is not None, name
    materials.delete_all_material_expressions(result)
    return result


def constant(mat, value, property_, y=0):
    node = materials.create_material_expression(mat, unreal.MaterialExpressionConstant, -240, y)
    node.set_editor_property("r", value)
    assert materials.connect_material_property(node, "", property_)


def color(mat, value):
    node = materials.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -240, 0)
    node.set_editor_property("constant", unreal.LinearColor(*value, 1.0))
    assert materials.connect_material_property(node, "", unreal.MaterialProperty.MP_BASE_COLOR)


def texture(mat, image, property_, sampler_type, output, y):
    node = materials.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -360, y)
    set_properties(node, texture=image, sampler_type=sampler_type)
    assert materials.connect_material_property(node, output, property_)


def spawn(actor_class, name, location, rotation=(0, 0, 0)):
    actor = actors.spawn_actor_from_class(actor_class, unreal.Vector(*location), unreal.Rotator(*rotation))
    assert actor is not None, name
    actor.set_actor_label(name)
    actor.set_editor_property("tags", [TAG])
    return actor


def main():
    active_project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    assert active_project == PROJECT.resolve(), f"Open only {PROJECT / 'CrateLab.uproject'}"
    for filename in [SOURCE / "Crate_game.fbx", SOURCE / "Textures" / "Crate_Wood_BaseColor.png",
                     SOURCE / "Textures" / "Crate_Wood_Roughness.png"]:
        assert filename.is_file(), str(filename)

    # The script deliberately uses the synchronous FBX factory and its documented options.
    # This toggle affects this editor process, not the user's other projects.
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "Interchange.FeatureFlags.Import.FBX 0")
    options = unreal.FbxImportUI()
    set_properties(options, automated_import_should_detect_type=False,
                   mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                   import_as_skeletal=False, import_mesh=True, import_animations=False,
                   import_materials=False, import_textures=False)
    mesh_options = options.get_editor_property("static_mesh_import_data")
    set_properties(mesh_options, combine_meshes=True, convert_scene=True,
                   convert_scene_unit=True, import_uniform_scale=1.0,
                   auto_generate_collision=False, build_nanite=False,
                   generate_lightmap_u_vs=True,
                   normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    mesh = import_asset(SOURCE / "Crate_game.fbx", "SM_Crate", unreal.StaticMesh,
                        options, unreal.FbxFactory())
    base = import_asset(SOURCE / "Textures" / "Crate_Wood_BaseColor.png",
                        "T_Crate_Wood_BaseColor", unreal.Texture2D, factory=unreal.TextureFactory())
    rough = import_asset(SOURCE / "Textures" / "Crate_Wood_Roughness.png",
                         "T_Crate_Wood_Roughness", unreal.Texture2D, factory=unreal.TextureFactory())
    base.set_editor_property("srgb", True)
    set_properties(rough, srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_MASKS)

    wood = material("M_Crate_Wood")
    texture(wood, base, unreal.MaterialProperty.MP_BASE_COLOR,
            unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, "RGB", 0)
    texture(wood, rough, unreal.MaterialProperty.MP_ROUGHNESS,
            unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, "R", 240)
    constant(wood, 0.0, unreal.MaterialProperty.MP_METALLIC, 480)
    iron = material("M_Crate_Iron")
    color(iron, (0.055, 0.065, 0.075))
    constant(iron, 0.7, unreal.MaterialProperty.MP_METALLIC, 200)
    constant(iron, 0.38, unreal.MaterialProperty.MP_ROUGHNESS, 360)
    floor_material = material("M_Preview_Floor")
    color(floor_material, (0.115, 0.14, 0.155))
    constant(floor_material, 0.85, unreal.MaterialProperty.MP_ROUGHNESS, 200)
    for mat in (wood, iron, floor_material):
        materials.recompile_material(mat)

    slots = mesh.get_editor_property("static_materials")
    assert len(slots) == 2, [str(slot.material_slot_name) for slot in slots]
    slot_names = []
    for index, slot in enumerate(slots):
        slot_name = str(slot.material_slot_name)
        slot_names.append(slot_name)
        assert "wood" in slot_name.lower() or "iron" in slot_name.lower(), slot_name
        mesh.set_material(index, iron if "iron" in slot_name.lower() else wood)
    bounds = mesh.get_bounds()
    dimensions = [2 * getattr(bounds.box_extent, axis) for axis in ("x", "y", "z")]
    assert all(abs(value - 100.0) < 0.05 for value in dimensions), dimensions
    bottom_z = bounds.origin.z - bounds.box_extent.z
    assert abs(bottom_z) < 0.05, bottom_z
    assert meshes.get_num_uv_channels(mesh, 0) >= 1
    meshes.remove_collisions(mesh)
    assert meshes.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX) >= 0
    assert meshes.get_simple_collision_count(mesh) == 1
    mesh.get_editor_property("body_setup").set_editor_property(
        "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)

    # Rebuild only actors created by this script in this task's preview map.
    if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
        assert levels.load_level(LEVEL)
        for actor in actors.get_all_level_actors():
            if actor.actor_has_tag(TAG):
                assert actors.destroy_actor(actor)
    else:
        assert levels.new_level(LEVEL)
    crate = spawn(unreal.StaticMeshActor, "Crate_1m", (0, 0, 0))
    crate_component = crate.get_component_by_class(unreal.StaticMeshComponent)
    crate_component.set_static_mesh(mesh)
    crate_component.set_collision_profile_name("BlockAll")
    floor = spawn(unreal.StaticMeshActor, "Preview_Floor", (0, 0, -5))
    floor.set_actor_scale3d(unreal.Vector(12, 12, 0.1))
    floor_component = floor.get_component_by_class(unreal.StaticMeshComponent)
    floor_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube.Cube"))
    floor_component.set_material(0, floor_material)
    floor_component.set_collision_profile_name("BlockAll")

    sun = spawn(unreal.DirectionalLight, "Preview_Sun", (0, 0, 500), (-45, -35, 0))
    sun_component = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun_component.set_intensity(3.5)
    sun_component.set_editor_property("atmosphere_sun_light", True)
    spawn(unreal.SkyAtmosphere, "Preview_Atmosphere", (0, 0, 0))
    sky = spawn(unreal.SkyLight, "Preview_SkyLight", (0, 0, 300))
    sky_component = sky.get_component_by_class(unreal.SkyLightComponent)
    sky_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky_component.set_intensity(1.0)
    sky_component.set_editor_property("real_time_capture", True)
    fill = spawn(unreal.RectLight, "Preview_Fill", (-180, -180, 230))
    fill.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(
        fill.get_actor_location(), unreal.Vector(0, 0, 50)), False)
    fill_component = fill.get_component_by_class(unreal.RectLightComponent)
    fill_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    fill_component.set_intensity(20.0)
    set_properties(fill_component, source_width=200.0, source_height=200.0)

    camera = spawn(unreal.CameraActor, "Preview_Camera", (235, -290, 200))
    camera_rotation = unreal.MathLibrary.find_look_at_rotation(camera.get_actor_location(), unreal.Vector(0, 0, 50))
    camera.set_actor_rotation(camera_rotation, False)
    camera.get_component_by_class(unreal.CameraComponent).set_field_of_view(45.0)
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    spawn(unreal.PlayerStart, "PlayerStart", (300, -300, 100))
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        camera.get_actor_location(), camera_rotation)
    actors.set_selected_level_actors([crate])

    for asset in (mesh, base, rough, wood, iron, floor_material):
        assert unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), asset.get_path_name()
    assert levels.save_current_level()
    map_file = PROJECT / "Content" / CONTENT.removeprefix("/Game/") / "CratePreview.umap"
    assert map_file.is_file(), str(map_file)
    engine_config = PROJECT / "Config" / "DefaultEngine.ini"
    config = engine_config.read_text(encoding="utf-8")
    lines = [line for line in config.splitlines()
             if not line.startswith(("EditorStartupMap=", "GameDefaultMap="))]
    section = "[/Script/EngineSettings.GameMapsSettings]"
    index = lines.index(section) + 1
    lines[index:index] = [f"EditorStartupMap={LEVEL}", f"GameDefaultMap={LEVEL}"]
    engine_config.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report.update(passed=True, engine_version=unreal.SystemLibrary.get_engine_version(),
                  mesh=mesh.get_path_name(), dimensions_cm=dimensions, bottom_z_cm=bottom_z,
                  material_slots=slot_names, simple_collision_count=1,
                  uv_channels=meshes.get_num_uv_channels(mesh, 0),
                  vertices=meshes.get_number_verts(mesh, 0),
                  base_color_srgb=base.get_editor_property("srgb"),
                  roughness_srgb=rough.get_editor_property("srgb"),
                  camera=camera.get_actor_label(), map_file=str(map_file),
                  actor_count=len(actors.get_all_level_actors()),
                  runtime_collision_tested=False, visual_review_pending=True)


try:
    main()
except Exception:
    report["error"] = traceback.format_exc()
    unreal.log_error(report["error"])
    raise
finally:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    unreal.log("CRATE_UNREAL_VALIDATION " + json.dumps(report, ensure_ascii=False))
