# 흑가시 / Blackthorn

실사풍 게임용 장검입니다. 중앙 홈과 끝으로 갈수록 얇아지는 양날 칼날, 검게 마감한 가드, 나선형 가죽 손잡이, 황동 선 장식과 다면체 폼멜로 구성했습니다. 특정 역사 유물의 복제품은 아닙니다.

## 파일

- `Blackthorn.blend`: 편집 원본. 텍스처를 내부에 포함했습니다.
- `Blackthorn_game.glb`: PBR 재질과 텍스처를 포함한 게임용 모델.
- `Blackthorn_game.fbx`: 게임용 모델. `Textures`의 PNG와 함께 사용합니다.
- `Blackthorn_hero.png`: 전체 미리보기.
- `Blackthorn_detail.png`: 손잡이와 가드 근접 미리보기.
- `Blackthorn_front.png`, `Blackthorn_side.png`: 정면과 측면 확인용 렌더.
- `Blackthorn_validation.json`: 원본 재열기 및 GLB·FBX 재가져오기 검사 결과.

작업 폴더의 `Open_Blender_Blackthorn.cmd`를 실행하면 Blender에서 열립니다. 스튜디오는 뷰포트에서 숨겨 두었으며 렌더에는 포함됩니다. `F12`로 전체 미리보기를 다시 렌더할 수 있습니다.

## 모델 규격

- 전체 길이: 1.237m. 가드 폭: 0.290m. 최대 두께: 0.034m.
- 메시 1개, 재질 1개, 삼각형 12,268개.
- 편집 가능한 부품 선택용 버텍스 그룹 20개.
- 원점: 손잡이 중앙. Blender에서 칼끝 방향은 로컬 `+Z`, 앞면은 `-Y`.
- 2048×2048 Base Color, Roughness, Metallic, Normal 이미지.
- 노멀맵: OpenGL 방식의 접선 공간 `+Y`.
- 금속·검은 금속·가죽·황동이 하나의 아틀라스를 공유합니다. 표면 UV는 의도적으로 겹치며, 별도의 라이트맵 UV는 없습니다.

GLB·FBX에는 검만 들어갑니다. 조명·카메라·배경은 제외했습니다. Blender 원본의 Triangulate 모디파이어는 게임 내보내기의 삼각형 분할을 고정합니다. 원본 메시의 면과 버텍스 그룹은 편집할 수 있습니다.

## 게임에서 사용하기

GLB는 재질이 포함되어 있습니다. FBX는 엔진 재질에서 `Textures`의 Base Color, Metallic, Roughness, Normal을 각각 연결하세요. Base Color만 색상 텍스처로 사용하고 나머지는 데이터 텍스처로 사용합니다. 엔진이 Smoothness를 요구하면 `1 - Roughness`로 변환합니다. 노멀맵은 대상 엔진의 Y 방향 설정에 맞춰 연결하세요.

캐릭터 손 소켓에는 손잡이 중앙 원점을 맞춥니다. 최종 크기와 방향은 엔진의 단위 및 축 변환을 확인하세요. 공격 판정, 충돌체, 애니메이션, LOD는 포함하지 않았습니다.

Blender에서 GLB·FBX를 다시 가져와 크기, 원점, 삼각형 수, UV, 재질 수를 검사했습니다. 닫힌 메시 구조와 패킹된 텍스처도 확인했습니다. 실제 Unity·Unreal 프로젝트 연결과 런타임 테스트는 아직 진행하지 않았습니다.

## 재생성

작업 폴더에서 실행합니다. 이 명령은 이 검의 생성 파일을 덮어씁니다. 직접 편집한 파일은 다른 이름으로 보관하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python '.\scripts\build_blackthorn.py'
```
