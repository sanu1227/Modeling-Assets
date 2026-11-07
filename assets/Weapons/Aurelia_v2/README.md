# 아우렐리아 v2 — Sovereign Filigree

아우렐리아의 기본 실루엣을 유지하며 장식의 입체감과 세부 표현을 높인 상세 모델입니다. 원래 아우렐리아와 흑가시 파일은 보존했습니다.

## 달라진 부분

- 가드의 단순 선 장식을 입체 잎사귀, 말린 덩굴 문양과 작은 꽃 장식으로 교체했습니다.
- 가드와 보석 테두리에 작은 금속 알갱이와 겹 테두리를 추가했습니다.
- 중앙 보석을 더 잘게 분할하고, 주변에 작은 수정과 실제 고정 발톱을 배치했습니다.
- 칼날의 금빛 곡선 문양이 칼날 표면 높이를 따라 밀착하도록 만들었습니다.
- 손잡이의 이중 금속 끈, 봉제점, 장식 고리와 폼멜의 잎사귀·보석 띠를 보강했습니다.
- 금속, 에나멜과 가죽을 위한 PBR 아틀라스를 4096×4096으로 높였습니다.

## 열기와 미리보기

작업 폴더의 `Open_Blender_Aurelia_v2.cmd`를 실행하면 원본이 열립니다. 스튜디오는 뷰포트에서 숨겨져 있으며 `F12` 렌더에는 표시됩니다.

- `Aurelia_v2_comparison.png`: 기존 버전과 수정 버전의 손잡이 비교.
- `Aurelia_v2_hero.png`: 전체 렌더.
- `Aurelia_v2_detail.png`: 손잡이·가드·폼멜 확대.
- `Aurelia_v2_guard_macro.png`: 보석 세팅과 가드 초근접 렌더.
- `Aurelia_v2_front.png`, `Aurelia_v2_side.png`: 형태 확인용 렌더.

## 모델과 내보내기

- `Aurelia_v2.blend`: 텍스처를 포함한 편집 원본.
- `Aurelia_v2_game.glb`: 모델과 PBR 텍스처를 포함한 내보내기.
- `Aurelia_v2_game.fbx`: FBX 모델. `Textures`의 PNG와 함께 사용합니다.
- 길이 약 1.330m, 가드 폭 약 0.357m, 최대 두께 약 0.0493m.
- 메시 1개, 재질 3개, 삼각형 109,300개, 부품 선택용 버텍스 그룹 356개.
- 손잡이 중앙 피벗. Blender 기준 칼끝 `+Z`, 앞면 `-Y`.
- 4K Base Color, Roughness, Metallic, Normal. 노멀맵은 OpenGL 접선 공간 `+Y`입니다.
- 표면 UV를 의도적으로 공유합니다. 별도의 라이트맵 UV는 없습니다.

이 버전은 작은 장식도 실제 메시로 표현한 근접 관찰용 상세 모델입니다. 자동 LOD, 충돌체와 공격 판정은 포함하지 않습니다. 실제 게임의 시점과 동시 표시 수에 따른 성능은 아직 측정하지 않았습니다.

## 보석 재질

청색 보석은 투과율 0.72, IOR 1.76의 재질입니다. GLB는 `KHR_materials_transmission`을 사용하므로 이를 지원하는 렌더러가 필요합니다. FBX를 사용하는 엔진에서는 보석의 투과·굴절·코팅을 해당 엔진 재질에서 설정해야 합니다. 작은 밝은 수정은 별도 불투명 코팅 재질입니다.

Base Color는 색상 텍스처, Roughness·Metallic·Normal은 데이터 텍스처로 사용합니다. Smoothness가 필요한 경우 `1 - Roughness`로 변환합니다. 노멀맵 Y 방향과 단위·축 변환은 대상 엔진의 설정에 맞추세요.

## 검증

`Aurelia_v2_validation.json`에 GLB·FBX 재가져오기 후 실제 버텍스 범위, 삼각형 수, UV, 재질 수와 원점을 검사한 결과가 있습니다. 닫힌 메시, 퇴화 삼각형, 유한 좌표, 저장본 재열기와 패킹된 텍스처를 확인했습니다. 이전 검들의 원본·내보내기·제작 스크립트는 SHA-256이 유지되었습니다. Unity·Unreal 실행 검증은 아직 하지 않았습니다.

## 재생성

아래 명령은 v2 생성 파일을 덮어씁니다. 직접 편집한 결과는 다른 이름으로 보관하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python '.\scripts\build_aurelia_v2.py'
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python '.\scripts\render_aurelia_v2_comparison.py'
```
