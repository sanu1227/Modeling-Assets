# 아우렐리아 / Aurelia — Royal Dawn

금빛 날개형 가드와 청색 보석을 갖춘 실사풍 판타지 장검입니다. 흑가시와 별도로 제작했습니다. 칼날의 금빛 월계수 문양, 청색 에나멜 장식, 열린 덩굴 장식, 가죽 손잡이의 금속 나선과 태양 형태의 폼멜을 앞뒤 양면에 구성했습니다.

## 열기

작업 폴더의 `Open_Blender_Aurelia.cmd`를 실행하면 Blender에서 열립니다. 스튜디오 배경과 조명은 뷰포트에서 숨겨 두었습니다. `F12`로 전체 렌더를 볼 수 있습니다.

- `Aurelia.blend`: 편집 원본. PBR 텍스처를 내부에 포함했습니다.
- `Aurelia_game.glb`: 텍스처와 재질을 포함한 모델.
- `Aurelia_game.fbx`: 엔진용 모델. `Textures`의 PNG와 함께 사용합니다.
- `Aurelia_hero.png`: 전체 미리보기.
- `Aurelia_detail.png`: 가드·손잡이·폼멜 근접 렌더.
- `Aurelia_front.png`, `Aurelia_side.png`: 정면과 측면 렌더.
- `Aurelia_validation.json`: 파일 재가져오기와 기존 흑가시 보존 검사 결과.

## 모델 규격

- 길이 약 1.330m, 가드 폭 약 0.355m, 최대 두께 약 0.0504m.
- 메시 1개, 재질 2개, 삼각형 33,422개.
- 편집 시 부품을 선택할 수 있는 버텍스 그룹 138개.
- 2048×2048 Base Color, Roughness, Metallic, Normal 아틀라스.
- 보석은 별도 불투명 PBR 재질입니다. 파란색, 낮은 거칠기, 코팅과 실제 절단면으로 표현했습니다.
- 손잡이 중앙이 원점입니다. Blender에서 칼끝은 로컬 `+Z`, 앞면은 `-Y`입니다.
- 노멀맵은 OpenGL 방식의 접선 공간 `+Y`입니다.
- 표면 UV는 의도적으로 겹칩니다. 별도 라이트맵 UV는 없습니다.

## 엔진에 가져오기

GLB에는 이미지와 재질이 포함됩니다. FBX는 엔진의 재질에서 `Textures`의 Base Color, Metallic, Roughness, Normal을 연결하세요. Base Color만 색상 텍스처로 사용하고 나머지는 데이터 텍스처로 사용합니다. Smoothness를 쓰는 재질에서는 `1 - Roughness`로 변환합니다. 보석 재질의 색상과 코팅은 대상 엔진의 셰이더에 맞게 확인하세요.

검의 원점을 손 소켓에 맞추고, 엔진의 축과 단위 변환을 확인하세요. 금빛 장식은 실제 메시로 만든 상세 모델입니다. 여러 자루를 동시에 표시하거나 멀리 배치할 때 사용할 LOD는 포함하지 않았습니다. 충돌체·공격 판정·애니메이션도 포함하지 않았습니다.

## 검증 범위

Blender에서 GLB·FBX를 재가져와 실제 버텍스 경계, 크기, 원점, 삼각형 수, UV와 재질 수를 검사합니다. 비정상 열린 모서리, 퇴화 삼각형, 유한하지 않은 좌표도 검사합니다. 저장한 `.blend`를 다시 열어 텍스처 포함 여부를 확인합니다.

흑가시의 `.blend`, `.glb`, `.fbx`와 생성 스크립트는 SHA-256으로 보존 여부를 확인합니다. 실제 Unity·Unreal 프로젝트 적용과 런타임 성능은 아직 테스트하지 않았습니다.

## 재생성

작업 폴더에서 실행합니다. 아우렐리아 생성 파일을 덮어쓰므로 직접 수정한 결과는 다른 이름으로 보관하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python '.\scripts\build_aurelia.py'
```
