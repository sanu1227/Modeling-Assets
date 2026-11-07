# 청운검 v2 — Black Gold Twin Dragons

흑색·금색에 진홍색 검수를 조합한 동양풍 판타지 직검입니다. 가드를 입체 용머리, 겹친 비늘, 가지 뿔, 송곳니와 수염, 아래가 뚫린 구름 장식으로 재제작했습니다. 손잡이와 고리 폼멜은 검은 옻칠을 표현하며 금색 테두리와 회문을 넣었습니다. 이전 청운검은 별도 폴더에 보존했습니다.

## 파일

- `AzureDragon_v2.blend`: 4K 텍스처를 내부에 포함한 Blender 편집 원본.
- `AzureDragon_v2_game.glb`: PBR 재질과 이미지를 포함한 모델.
- `AzureDragon_v2_game.fbx`: 모델. `Textures`의 PNG와 함께 사용합니다.
- `AzureDragon_v2_comparison.png`: 실제 이전 모델과 새 모델의 전후 비교 렌더.
- `AzureDragon_v2_hero.png`: 전체 모습.
- `AzureDragon_v2_detail.png`: 가드·손잡이·검수 확대.
- `AzureDragon_v2_guard_macro.png`: 용머리 가드 확대.
- `AzureDragon_v2_front.png`, `AzureDragon_v2_side.png`: 정면·측면 렌더.
- `AzureDragon_v2_validation.json`: 원본 재열기 및 GLB·FBX 재가져오기 검사 결과.

작업 폴더의 `Open_Blender_AzureDragon_v2.cmd`로 편집 원본을 엽니다. 스튜디오는 뷰포트에서 숨겨져 있으며 F12 렌더에는 포함됩니다.

## 규격과 게임 적용

- 검 본체 길이 1.100m, 검수 포함 높이 약 1.351m.
- 최대 폭 약 0.317m, 최대 두께 약 0.0503m.
- 메시 1개, 재질 1개, 삼각형 110,608개, 부품 선택용 버텍스 그룹 65개.
- 손잡이 중앙 피벗. Blender 기준 칼끝 +Z, 앞면 -Y.
- 4096×4096 Base Color, Roughness, Metallic, Normal 아틀라스.
- 노멀맵: OpenGL 접선 공간 +Y. 의도적으로 공유하는 표면 UV이며 별도 라이트맵 UV는 없습니다.

FBX 사용 시 `Textures`의 이미지를 엔진 재질에 연결하세요. Base Color만 색상 텍스처로, 나머지는 데이터 텍스처로 사용합니다. Smoothness는 1 − Roughness로 변환합니다. 대상 엔진의 축·단위·노멀맵 Y 방향에 맞춰 설정하세요.

검수는 실제 메시로 만든 정적인 장식입니다. 골격과 천·끈 물리는 포함하지 않았으며 `Tassel` 버텍스 그룹으로 후속 리깅이 가능합니다. 자동 LOD, 충돌체, 공격 판정과 애니메이션은 포함하지 않았습니다. 실제 게임 엔진에서 성능은 검증하지 않았습니다.

## 검증과 재생성

검증 스크립트는 닫힌 메시, 퇴화 삼각형, 유한 좌표, UV, 원점과 스케일을 검사합니다. GLB·FBX를 다시 가져와 실제 버텍스 경계와 삼각형·재질 수를 비교합니다. 저장한 Blender 원본을 다시 열어 텍스처 패킹을 확인하며 이전 무기 파일의 SHA-256을 검사합니다. 실제 결과는 `AzureDragon_v2_validation.json`을 확인하세요.

아래 명령은 v2 생성 파일을 덮어씁니다. 직접 편집한 결과는 다른 이름으로 보관하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python '.\scripts\build_azure_dragon_v2.py'
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python '.\scripts\render_azure_dragon_v2_comparison.py'
```
