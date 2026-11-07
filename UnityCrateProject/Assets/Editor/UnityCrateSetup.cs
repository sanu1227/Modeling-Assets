// Copy into Assets/Editor, then run Tools > Crate > Build and Verify.
// Batch: Unity.exe -batchmode -force-d3d11 -projectPath <project> -executeMethod CrateSetup.Run -quit
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

public static class CrateSetup
{
    const string Art = "Assets/Art/Crate";
    const string ModelPath = Art + "/Crate_game.fbx";
    const string PrefabPath = Art + "/Crate.prefab";
    const string ScenePath = "Assets/Scenes/CrateTest.unity";
    const float Tolerance = 0.001f;

    [Serializable]
    sealed class Report
    {
        public string unityVersion = Application.unityVersion;
        public bool passed, geometryPassed, physicsPassed, previewPassed;
        public int meshes, vertices, triangles, uvCount, subMeshes;
        public Vector3 sizeMeters, boundsMinMeters, colliderCenter, colliderSize;
        public float smoothnessMin = 1, smoothnessMax;
        public float dropStartHeight, dropHalfSecondHeight, dropFinalHeight;
        public float dropMinimumHeight, dropFinalSpeed, dropHorizontalDrift;
        public string scene = ScenePath, prefab = PrefabPath, preview, error;
        public string[] materials = { "M_Crate_Wood", "M_Crate_Iron" };
    }

    [MenuItem("Tools/Crate/Build and Verify")]
    public static void Run()
    {
        string project = Directory.GetParent(Application.dataPath).FullName;
        string output = Path.Combine(project, "Validation");
        Directory.CreateDirectory(output);
        var report = new Report { preview = Path.Combine(output, "Crate_preview.png") };
        try
        {
            Require(!EditorApplication.isPlaying, "Stop Play Mode before rebuilding the test scene.");
            Require(GraphicsSettings.currentRenderPipeline != null,
                "Create this project from the installed URP template first.");
            if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
                throw new OperationCanceledException("Scene creation cancelled; existing changes preserved.");

            ImportSource(project);
            Shader shader = Shader.Find("Universal Render Pipeline/Lit");
            Require(shader != null, "URP Lit shader is missing.");
            var baseColor = ConfigureTexture(Art + "/Textures/Crate_Wood_BaseColor.png", true);
            var packed = MakeMetallicSmoothness(report);
            Material wood = MaterialAsset("M_Crate_Wood", shader, Color.white, 0, 1);
            wood.SetTexture("_BaseMap", baseColor);
            wood.SetTexture("_MetallicGlossMap", packed);
            wood.EnableKeyword("_METALLICSPECGLOSSMAP");
            wood.DisableKeyword("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A");
            wood.SetFloat("_SmoothnessTextureChannel", 0);
            EditorUtility.SetDirty(wood);
            // Blender's Principled color is linear; Unity's Color property uses sRGB values.
            Material iron = MaterialAsset("M_Crate_Iron", shader,
                new Color(0.055f, 0.065f, 0.075f, 1).gamma, 0.7f, 0.62f);

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("Crate");
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            Require(model != null, "FBX import did not produce a model asset.");
            var modelInstance = (GameObject)PrefabUtility.InstantiatePrefab(model, scene);
            modelInstance.transform.SetParent(root.transform, false);
            foreach (var renderer in root.GetComponentsInChildren<MeshRenderer>())
            {
                renderer.sharedMaterials = renderer.sharedMaterials.Select(material =>
                {
                    Require(material != null, "An FBX material slot is missing.");
                    if (material.name.Contains("M_Crate_Wood")) return wood;
                    if (material.name.Contains("M_Crate_Iron")) return iron;
                    throw new InvalidOperationException("Unexpected FBX material: " + material.name);
                }).ToArray();
            }
            ValidateGeometry(root, report);
            var box = root.AddComponent<BoxCollider>();
            box.center = new Vector3(0, 0.5f, 0);
            box.size = Vector3.one;
            report.colliderCenter = box.center;
            report.colliderSize = box.size;
            Require(root.GetComponentsInChildren<Collider>().Length == 1, "Expected one box collider.");
            var prefab = PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            Require(prefab != null, "Saving the crate prefab failed.");
            root.name = "Crate_Static";
            root.transform.position = new Vector3(-0.8f, 0, 0);

            var drop = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
            drop.name = "Crate_DropTest_PlayToDrop";
            drop.transform.position = new Vector3(1, 2.2f, 0);
            var body = drop.AddComponent<Rigidbody>();
            body.mass = 8;
            body.interpolation = RigidbodyInterpolation.Interpolate;
            body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Ground";
            floor.transform.position = new Vector3(0, -0.1f, 0);
            floor.transform.localScale = new Vector3(8, 0.2f, 6);
            floor.GetComponent<Renderer>().sharedMaterial =
                MaterialAsset("M_Ground", shader, new Color(0.22f, 0.25f, 0.28f), 0, 0.15f);
            TestDrop(drop, report);

            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.3f, 0.32f, 0.36f);
            var light = new GameObject("Key Light").AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.5f;
            light.color = new Color(1, 0.92f, 0.82f);
            light.shadows = LightShadows.Soft;
            light.transform.rotation = Quaternion.Euler(45, -35, 0);
            var camera = new GameObject("Main Camera").AddComponent<Camera>();
            camera.tag = "MainCamera";
            camera.transform.position = new Vector3(4.5f, 3.8f, -5.5f);
            camera.transform.LookAt(new Vector3(0.1f, 1.2f, 0));
            camera.orthographic = true;
            camera.orthographicSize = 2.3f;
            camera.nearClipPlane = 0.1f;
            camera.farClipPlane = 100;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0.075f, 0.095f, 0.12f);
            camera.gameObject.AddComponent<AudioListener>();
            Directory.CreateDirectory("Assets/Scenes");
            Require(EditorSceneManager.SaveScene(scene, ScenePath), "Saving the scene failed.");
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            AssetDatabase.SaveAssets();
            RenderPreview(camera, report);
            report.passed = report.geometryPassed && report.physicsPassed && report.previewPassed;
            Debug.Log("CRATE_UNITY_VALIDATION_OK " + JsonUtility.ToJson(report));
        }
        catch (Exception exception)
        {
            report.error = exception.ToString();
            throw;
        }
        finally
        {
            File.WriteAllText(Path.Combine(output, "Crate_validation.json"), JsonUtility.ToJson(report, true));
        }
    }

    static void ImportSource(string project)
    {
        string source = Path.Combine(Directory.GetParent(project).FullName, "assets", "Crate");
        Directory.CreateDirectory(Art + "/Textures");
        Directory.CreateDirectory(Art + "/Materials");
        foreach (string relative in new[] { "Crate_game.fbx", "Textures/Crate_Wood_BaseColor.png", "Textures/Crate_Wood_Roughness.png" })
        {
            string original = Path.Combine(source, relative);
            Require(File.Exists(original), "Missing source asset: " + original);
            File.Copy(original, Art + "/" + relative, true);
        }
        AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        var importer = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
        Require(importer != null, "FBX importer is unavailable.");
        importer.globalScale = 1;
        importer.useFileScale = true;
        importer.bakeAxisConversion = true;
        importer.importAnimation = false;
        importer.importCameras = false;
        importer.importLights = false;
        importer.addCollider = false;
        importer.isReadable = true;
        importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
        importer.SaveAndReimport();
    }

    static Texture2D ConfigureTexture(string path, bool srgb)
    {
        var importer = (TextureImporter)AssetImporter.GetAtPath(path);
        Require(importer != null, "Texture importer is unavailable: " + path);
        importer.textureType = TextureImporterType.Default;
        importer.sRGBTexture = srgb;
        importer.alphaSource = TextureImporterAlphaSource.FromInput;
        importer.alphaIsTransparency = false;
        importer.textureCompression = TextureImporterCompression.Uncompressed;
        importer.SaveAndReimport();
        return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
    }

    static Texture2D MakeMetallicSmoothness(Report report)
    {
        const string roughPath = Art + "/Textures/Crate_Wood_Roughness.png";
        const string packedPath = Art + "/Textures/Crate_Wood_MetallicSmoothness.png";
        ConfigureTexture(roughPath, false);
        var importer = (TextureImporter)AssetImporter.GetAtPath(roughPath);
        bool wasReadable = importer.isReadable;
        Texture2D packed = null;
        try
        {
            importer.isReadable = true;
            importer.SaveAndReimport();
            var roughness = AssetDatabase.LoadAssetAtPath<Texture2D>(roughPath);
            Require(roughness.width == 1024 && roughness.height == 1024, "Expected 1024-square roughness map.");
            Color32[] pixels = roughness.GetPixels32();
            for (int i = 0; i < pixels.Length; i++)
            {
                byte smoothness = (byte)(255 - pixels[i].r);
                report.smoothnessMin = Mathf.Min(report.smoothnessMin, smoothness / 255f);
                report.smoothnessMax = Mathf.Max(report.smoothnessMax, smoothness / 255f);
                pixels[i] = new Color32(0, 0, 0, smoothness);
            }
            Require(report.smoothnessMin > 0 && report.smoothnessMax < 0.5f, "Unexpected wood smoothness range.");
            packed = new Texture2D(roughness.width, roughness.height, TextureFormat.RGBA32, false, true);
            packed.SetPixels32(pixels);
            packed.Apply(false, false);
            File.WriteAllBytes(packedPath, packed.EncodeToPNG());
        }
        finally
        {
            if (packed != null) Object.DestroyImmediate(packed);
            importer.isReadable = wasReadable;
            importer.SaveAndReimport();
        }
        AssetDatabase.ImportAsset(packedPath, ImportAssetOptions.ForceSynchronousImport);
        return ConfigureTexture(packedPath, false);
    }

    static Material MaterialAsset(string name, Shader shader, Color color, float metallic, float smoothness)
    {
        string path = Art + "/Materials/" + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null)
        {
            material = new Material(shader) { name = name };
            AssetDatabase.CreateAsset(material, path);
        }
        material.shader = shader;
        material.shaderKeywords = Array.Empty<string>();
        material.SetColor("_BaseColor", color);
        material.SetFloat("_Metallic", metallic);
        material.SetFloat("_Smoothness", smoothness);
        material.SetFloat("_WorkflowMode", 1);
        EditorUtility.SetDirty(material);
        return material;
    }

    static void ValidateGeometry(GameObject root, Report report)
    {
        var filters = root.GetComponentsInChildren<MeshFilter>();
        Require(filters.Length == 1, "Expected exactly one exported mesh.");
        var mesh = filters[0].sharedMesh;
        report.meshes = filters.Length;
        report.vertices = mesh.vertexCount;
        report.triangles = mesh.triangles.Length / 3;
        report.uvCount = mesh.uv.Length;
        report.subMeshes = mesh.subMeshCount;
        Require(report.triangles == 5192, "Triangle count differs from the verified Blender export.");
        Require(report.subMeshes == 2, "Expected wood and iron submeshes.");
        Require(report.uvCount == report.vertices, "UV count must match vertex count.");
        Require(mesh.uv.All(uv => float.IsFinite(uv.x) && float.IsFinite(uv.y)), "UV contains invalid numbers.");
        Require(mesh.uv.Max(uv => uv.x) - mesh.uv.Min(uv => uv.x) > 0.1f, "UVs collapsed on the U axis.");
        Require(mesh.uv.Max(uv => uv.y) - mesh.uv.Min(uv => uv.y) > 0.1f, "UVs collapsed on the V axis.");
        Bounds bounds = root.GetComponentInChildren<MeshRenderer>().bounds;
        report.sizeMeters = bounds.size;
        report.boundsMinMeters = bounds.min;
        Require((bounds.size - Vector3.one).sqrMagnitude < Tolerance * Tolerance,
            "Expected 1 x 1 x 1 metres; check FBX unit conversion. Actual: " + bounds.size);
        Require(Mathf.Abs(bounds.min.y) < Tolerance &&
            Mathf.Abs(bounds.center.x) < Tolerance && Mathf.Abs(bounds.center.z) < Tolerance,
            "Expected the origin at the crate's bottom centre.");
        Require(root.GetComponentsInChildren<MeshRenderer>().Single().sharedMaterials.Length == 2,
            "Expected two material slots.");
        report.geometryPassed = true;
    }

    static void TestDrop(GameObject drop, Report report)
    {
        // Only the newly created demonstration scene is open. Restore the drop pose for Play Mode.
        var body = drop.GetComponent<Rigidbody>();
        Vector3 start = drop.transform.position;
        Quaternion rotation = drop.transform.rotation;
        SimulationMode previousMode = Physics.simulationMode;
        try
        {
            Physics.simulationMode = SimulationMode.Script;
            report.dropStartHeight = start.y;
            report.dropMinimumHeight = start.y;
            Physics.SyncTransforms();
            for (int step = 0; step < 150; step++)
            {
                Physics.Simulate(0.02f);
                report.dropMinimumHeight = Mathf.Min(report.dropMinimumHeight, body.position.y);
                if (step == 24) report.dropHalfSecondHeight = body.position.y;
            }
            report.dropFinalHeight = body.position.y;
            report.dropFinalSpeed = body.linearVelocity.magnitude;
            report.dropHorizontalDrift = Vector2.Distance(new Vector2(start.x, start.z),
                new Vector2(body.position.x, body.position.z));
            Require(report.dropHalfSecondHeight < start.y - 0.5f, "Crate did not fall under gravity.");
            Require(report.dropMinimumHeight > -0.03f, "Crate passed through the ground.");
            Require(Mathf.Abs(report.dropFinalHeight) < 0.03f, "Crate did not land at floor height after 3 seconds.");
            Require(report.dropFinalSpeed < 0.1f && report.dropHorizontalDrift < 0.03f,
                "Crate did not settle with a stable collision.");
            report.physicsPassed = true;
        }
        finally
        {
            body.linearVelocity = Vector3.zero;
            body.angularVelocity = Vector3.zero;
            body.position = start;
            body.rotation = rotation;
            drop.transform.SetPositionAndRotation(start, rotation);
            body.WakeUp();
            Physics.SyncTransforms();
            Physics.simulationMode = previousMode;
        }
    }

    static void RenderPreview(Camera camera, Report report)
    {
        Require(SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null, "Preview needs graphics; omit -nographics.");
        var target = RenderTexture.GetTemporary(1024, 1024, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
        RenderTexture previous = RenderTexture.active;
        Texture2D image = null;
        try
        {
            var request = new RenderPipeline.StandardRequest { destination = target };
            Require(RenderPipeline.SupportsRenderRequest(camera, request), "Active URP renderer does not support render requests.");
            RenderPipeline.SubmitRenderRequest(camera, request);
            RenderTexture.active = target;
            image = new Texture2D(1024, 1024, TextureFormat.RGB24, false);
            image.ReadPixels(new Rect(0, 0, 1024, 1024), 0, 0);
            image.Apply();
            Color32[] pixels = image.GetPixels32();
            Require(pixels.Max(pixel => (int)pixel.r) - pixels.Min(pixel => (int)pixel.r) > 20,
                "Rendered preview is blank or uniform.");
            Require(pixels.Count(pixel => pixel.r > 200 && pixel.b > 200 && pixel.g < 70) < pixels.Length / 100,
                "Preview contains magenta error-shader pixels.");
            File.WriteAllBytes(report.preview, image.EncodeToPNG());
            report.previewPassed = true;
        }
        finally
        {
            RenderTexture.active = previous;
            if (image != null) Object.DestroyImmediate(image);
            RenderTexture.ReleaseTemporary(target);
        }
    }

    static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
}
