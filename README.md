# Blender 나무 상자 실습

AI가 작성한 Blender Python 스크립트로 만든 게임용 나무 상자입니다. 외부 3D 생성 서비스나 유료 에셋을 사용하지 않았습니다.

## Blender 결과

- `Open_Blender_Crate.cmd`: 설치된 Blender 5.2.3에서 수정본을 엽니다.
- `assets/Crate/Crate_source.blend`: 1m 정육면체로 시작한 원본입니다.
- `assets/Crate/Crate_work.blend`: 판재, 프레임, 대각선 보강재, 못과 베벨을 추가한 수정본입니다.
- `assets/Crate/Crate_game.glb`: 이미지 재질을 포함한 모델입니다.
- `assets/Crate/Crate_game.fbx`: FBX 모델입니다. 텍스처는 `Textures`와 `Crate_game.fbm`에 있습니다.
- `assets/Crate/Crate_preview.png`: Blender에서 실제 렌더링한 미리보기입니다.
- `assets/Crate/Crate_validation.json`: 실제 생성 및 GLB·FBX 재임포트 검사 결과입니다.

모델은 1m 정육면체이며 원점은 바닥 중앙입니다. 메시 1개, 재질 2개, 삼각형 5,192개입니다. Base Color와 Roughness 이미지는 1024×1024입니다.

## Blender에서 수정하기

1. `Open_Blender_Crate.cmd`를 실행합니다.
2. `Crate_Game` 모델을 선택하고 `Tab`으로 Edit Mode에 들어갑니다.
3. 판재 위에서 `L`을 눌러 연결된 판재를 선택합니다. `G`로 이동하거나 `S`로 크기를 바꿉니다.
4. 모델 전체 크기는 Object Mode의 `N > Item > Dimensions`에서 확인합니다.
5. 작업본을 다른 이름으로 저장합니다. `scripts/create_crate.py`를 다시 실행하면 이 실습의 생성 파일이 다시 만들어집니다.

게임용 내보내기에는 상자만 선택합니다. 미리보기용 바닥·조명·카메라는 제외합니다. GLB는 이미지 재질이 포함되며, FBX는 텍스처 파일도 함께 전달합니다.

## 엔진 연결

Unity와 Unreal에서는 같은 FBX와 PNG를 사용합니다. Unity URP는 Roughness를 뒤집어 Smoothness로 변환하고, Unreal은 Roughness를 그대로 연결합니다. 두 엔진 모두 바닥 중앙 피벗과 박스 충돌을 사용합니다.

### Unity에서 결과 열기

Unity **6000.6.5f1 / URP 17.6.0**에서 실제 가져오기, 재질, 1m 크기, 낙하 충돌, 미리보기 렌더 검증을 통과했습니다.

1. PowerShell에서 다음 명령으로 프로젝트를 엽니다.

   ```powershell
   & 'C:\Program Files\Unity\Hub\Editor\6000.6.5f1\Editor\Unity.exe' -projectPath 'C:\Users\saenu\Documents\ChatGPT\모델링\UnityCrateProject'
   ```

2. Project 창에서 `Assets/Scenes/CrateTest.unity`를 더블 클릭합니다.
3. Hierarchy의 `Crate_Static`은 바닥에 놓인 상자입니다. `Crate_DropTest_PlayToDrop`은 공중의 시험용 상자입니다.
4. Play를 누르면 시험용 상자가 2.2m 높이에서 바닥으로 떨어집니다. Play를 끄면 시작 위치로 돌아갑니다.
5. 재사용할 상자는 `Assets/Art/Crate/Crate.prefab`입니다. 다른 씬으로 끌어 놓거나 더블 클릭해 구성 요소를 확인합니다. Box Collider의 Size는 `(1, 1, 1)`, Center는 `(0, 0.5, 0)`입니다.

검증 결과는 다음 파일에 있습니다.

- `UnityCrateProject/Validation/Crate_validation.json`: `passed`, `geometryPassed`, `physicsPassed`, `previewPassed` 모두 `true`입니다. 낙하 3초 후 높이와 속도는 모두 0입니다.
- `UnityCrateProject/Validation/Crate_preview.png`: Unity에서 실제 렌더링한 고정 상자와 낙하 시험 상자입니다.
- `logs/unity-crate-setup.log`: `CRATE_UNITY_VALIDATION_OK`와 종료 코드 0을 기록합니다.

### Blender 수정본을 Unity에 다시 반영하기

1. Blender 작업본을 별도 이름으로 저장한 뒤 수정합니다. 첫 연습에서는 전체 크기 1m, 바닥 중앙 원점, 재질 이름 `M_Crate_Wood`·`M_Crate_Iron`을 유지합니다.
2. Object Mode에서 `Crate_Game`만 선택하고 `File > Export > FBX`를 선택합니다. **Selected Objects**, 메시만 내보내기, Scale `1`, Forward `-Z`, Up `Y`, 애니메이션 끄기를 사용합니다.
3. 내보낼 파일을 `assets/Crate/Crate_game.fbx`로 지정합니다. 기존 실습 FBX를 교체하므로 이전 결과가 필요하면 먼저 복사해 보관합니다. 텍스처를 수정했다면 `assets/Crate/Textures`의 PNG도 함께 저장합니다.
4. Unity에서 `Tools > Crate > Build and Verify`를 실행합니다. 원본 FBX·PNG를 프로젝트로 복사하고 다시 가져온 뒤 재질, 프리팹, 시험 씬과 검증 결과를 재생성합니다.
5. `CrateTest.unity`에서 수정된 형태를 확인하고 Play로 충돌을 확인합니다. 검증 JSON과 미리보기 PNG도 갱신됩니다.

이 메뉴는 초기 상자의 **1m·삼각형 5,192개·재질 2개**를 검사합니다. 판재를 추가하거나 삭제해 삼각형 수가 바뀌면 검사가 실패합니다. 그런 모델은 별도 FBX로 `Assets`에 가져오고 새 크기에 맞춰 충돌을 조정합니다. 메뉴를 다시 실행하면 이 실습의 생성 재질·프리팹·씬을 다시 쓰므로, Unity에서 따로 편집한 결과는 다른 이름으로 저장해 둡니다.

설정 스크립트 원본은 `scripts/UnityCrateSetup.cs`, 프로젝트에서 실행되는 사본은 `UnityCrateProject/Assets/Editor/UnityCrateSetup.cs`입니다. 이 FBX 실습에는 glTFast를 추가 설치하지 않습니다.

### Unreal에서 결과 열기

**2026-10-24 Unreal Engine 5.8.4 설치, 모델 가져오기, 실제 낙하 충돌 검증과 미리보기 육안 확인을 완료했습니다.** 모델 크기는 약 `100 × 100 × 100cm`이며 바닥 중앙 원점, 재질 2개, UV 채널 1개, 박스 충돌 1개를 확인했습니다.

1. PowerShell에서 다음 명령으로 프로젝트를 엽니다.

   ```powershell
   & 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' 'C:\Users\saenu\Documents\ChatGPT\모델링\UnrealCrate\CrateLab.uproject'
   ```

2. Content Browser 또는 Content Drawer에서 `Content > CrateLab`을 엽니다. 엔진 내부 경로는 `/Game/CrateLab`입니다.
3. `CratePreview` 지도를 더블 클릭하면 완성한 상자와 미리보기 조명·카메라를 볼 수 있습니다.
4. `SM_Crate`를 다른 지도에 끌어 놓아 재사용합니다. 더블 클릭하면 Static Mesh Editor에서 재질과 충돌을 확인할 수 있습니다. 배치할 때 Scale `(1, 1, 1)`이 1m 크기입니다.

이 지도의 원본 상자는 고정되어 있습니다. 낙하 검증은 아래 스크립트가 만드는 임시 복사본으로 실행하며, 검증이 끝나면 제거합니다.

### Blender 수정본을 Unreal에 반영하고 검증하기

1. 앞의 Blender 내보내기 순서대로 `assets/Crate/Crate_game.fbx`와 필요한 PNG를 갱신합니다.
2. `CrateLab.uproject`에서 `File > Execute Python Script`를 선택하고 `scripts/setup_unreal_crate.py`를 실행합니다. FBX·텍스처·목재/철 재질·박스 충돌과 `CratePreview` 지도를 갱신합니다.
3. `Content > CrateLab > CratePreview` 지도를 열고, Play 또는 Simulate가 실행 중이면 중지합니다.
4. 다시 `File > Execute Python Script`에서 `scripts/verify_unreal_crate.py`를 실행합니다. 에디터가 SIE(Simulate In Editor)로 임시 상자를 떨어뜨려 3초 이상 관찰하고, 정지·바닥 충돌·기존 지도 보존 여부를 검사합니다. 검증이 끝날 때까지 에디터를 열어 둡니다.
5. 아래 런타임 JSON의 `status: "complete"`, `passed: true`와 갱신된 미리보기 PNG를 확인합니다. 검증 결과만으로 새 모델의 외관까지 확인되지는 않으므로 PNG도 직접 봅니다.

`setup_unreal_crate.py`는 `/Game/CrateLab`의 생성 에셋과 생성 태그가 붙은 액터를 다시 구성합니다. 따로 편집한 재질·상자·지도를 보관하려면 다른 이름으로 복제한 뒤 실행합니다. `verify_unreal_crate.py`는 지도를 저장하지 않고 임시 시험 액터를 정리합니다. 두 스크립트는 이 실습 프로젝트용이며, Python Script·Editor Scripting 플러그인이 프로젝트에 활성화되어 있습니다.

실제 확인 근거는 단계별로 나뉩니다.

- `logs/unreal_crate_validation.json`: 가져오기·크기·재질·UV·충돌 설정 검사 `passed: true`입니다. `runtime_collision_tested: false`, `visual_review_pending: true`는 **이 임포트 단계에서 아직 검사하지 않았다는 값**입니다.
- `logs/unreal_crate_runtime_validation.json`: 후속 실제 SIE 시험에서 `passed: true`, 낙하·착지·정지 검사 통과, 표본상 바닥 관통 미관측, `editor_actors_preserved: true`, `map_file_unchanged: true`를 확인했습니다.
- `logs/unreal_crate_preview.png`: 후속 시험에서 저장한 실제 에디터 미리보기이며, 현재 상자의 목재·철못 재질과 형태를 육안으로 확인했습니다.

## 도구 위치

Blender는 시스템 설정을 바꾸지 않는 ZIP 배포본으로 `tools/blender-5.2.3-windows-x64`에 설치했습니다. 공식 다운로드 파일의 SHA-256을 검증했습니다. Unity는 기존 설치를 재사용합니다. `tools`와 엔진 캐시는 Git 추적에서 제외했습니다.
