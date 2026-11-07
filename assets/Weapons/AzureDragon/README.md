# 청운검 / Cheongun — Azure Dragon

중국식 직검을 바탕으로 만든 동양풍 판타지 검입니다. 특정 역사 유물의 복제품은 아닙니다. 강철 양날, 용의 눈·뿔·수염을 표현한 금빛 가드, 옥색 손잡이, 구름 문양과 회문 장식, 가운데가 뚫린 옥 고리 폼멜, 붉은 매듭과 두 갈래 검수로 구성했습니다.

## 열기

작업 폴더의 `Open_Blender_AzureDragon.cmd`를 실행하면 Blender 원본이 열립니다. 스튜디오는 뷰포트에서 숨겨져 있으며 `F12` 렌더에는 포함됩니다.

- `AzureDragon.blend`: 텍스처를 내부에 포함한 편집 원본.
- `AzureDragon_game.glb`: 이미지와 PBR 재질을 포함한 모델.
- `AzureDragon_game.fbx`: 모델. `Textures`의 PNG와 함께 사용합니다.
- `AzureDragon_hero.png`: 전체 미리보기.
- `AzureDragon_detail.png`: 손잡이·폼멜·검수 확대.
- `AzureDragon_guard_macro.png`: 용머리 가드와 문양 확대.
- `AzureDragon_front.png`, `AzureDragon_side.png`: 정면과 측면 확인용 렌더.
- `AzureDragon_validation.json`: 원본 재열기, 내보내기 재가져오기 및 이전 모델 보존 검사 결과.

## 규격

- 검 본체 길이: 1.100m.
- 검수를 포함한 전체 세로 범위: 약 1.351m.
- 최대 폭: 약 0.227m. 최대 두께: 약 0.0411m.
- 메시 1개, 재질 1개, 삼각형 75,520개.
- 부품 선택용 버텍스 그룹 54개.
- 손잡이 중앙 피벗. Blender 기준 칼끝 `+Z`, 앞면 `-Y`.
- 4096×4096 Base Color, Roughness, Metallic, Normal 아틀라스.
- 노멀맵은 OpenGL 접선 공간 `+Y`. 표면 UV는 의도적으로 공유하며 별도 라이트맵 UV는 없습니다.

옥과 실은 모두 불투명 PBR 재질입니다. 별도의 투과 확장이나 알파 텍스처가 필요하지 않습니다. 검수의 가는 실과 금실도 실제 메시로 구성했습니다.

## 게임에서 사용하기

GLB는 재질과 이미지가 포함됩니다. FBX는 `Textures`의 Base Color, Metallic, Roughness, Normal을 엔진 재질에 연결하세요. Base Color만 색상 텍스처로, 나머지는 데이터 텍스처로 사용합니다. Smoothness가 필요하면 `1 - Roughness`로 변환합니다. 대상 엔진의 축·단위·노멀맵 Y 방향을 확인하세요.

검수는 정적인 장식입니다. 골격이나 천·끈 물리는 포함하지 않았습니다. Blender의 `Tassel`로 시작하는 버텍스 그룹으로 분리하여 후속 리깅에 사용할 수 있습니다. 자동 LOD, 충돌체, 공격 판정, 애니메이션과 실제 엔진 성능 검증은 포함하지 않았습니다.

## 검증과 재생성

GLB·FBX를 다시 가져와 실제 버텍스 경계, 삼각형 수, 원점, UV와 재질 수를 검사했습니다. 닫힌 메시, 퇴화 삼각형, 유한 좌표와 패킹된 텍스처를 확인했습니다. 흑가시·아우렐리아·아우렐리아 v2의 원본·내보내기·스크립트는 SHA-256이 유지되었습니다.

아래 명령은 청운검 생성 파일을 덮어씁니다. 직접 편집한 결과는 다른 이름으로 보관하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python '.\scripts\build_azure_dragon.py'
```
