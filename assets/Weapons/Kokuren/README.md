# 흑련 / Kokuren — Japanese-inspired Katana

완만하게 휜 외날, 하몬 표면 무늬, 검은 교차 손잡이 감기와 밝은 가죽 바탕, 금색 꽃·파도 장식을 조합한 게임용 판타지 카타나입니다. 특정 역사 유물의 복제품은 아닙니다. 구멍이 뚫린 츠바와 별도의 검은 옻칠 칼집, 진홍색 사게오 끈을 포함합니다.

## 파일

- `Kokuren.blend`: 텍스처를 내부에 포함한 Blender 편집 원본.
- `Kokuren_game.glb`: 검과 칼집, 공유 PBR 재질과 이미지가 포함된 모델.
- `Kokuren_game.fbx`: 검과 칼집 모델. `Textures`의 PNG와 함께 사용합니다.
- `Kokuren_hero.png`: 검과 칼집의 전체 모습.
- `Kokuren_hilt.png`: 손잡이 감기와 장식 확대.
- `Kokuren_tsuba.png`: 츠바의 투각 구조와 금색 꽃 장식 확대.
- `Kokuren_front.png`: 곡률과 비율 확인용 정면 렌더.
- `Kokuren_blade_detail.png`: 날과 하몬 확대.
- `Kokuren_validation.json`: 메시·내보내기·원본 보존 검사 결과.

작업 폴더의 `Open_Blender_Kokuren.cmd`로 원본을 엽니다. 스튜디오는 뷰포트에서 숨겨져 있으며 F12 렌더에는 포함됩니다.

## 규격

- 검 전체 세로 길이 약 1.022m, 날의 세로 길이 약 0.751m.
- `SM_Kokuren_Katana`: 삼각형 76,058개. 손잡이 중앙 피벗.
- `SM_Kokuren_Saya`: 삼각형 41,836개. 칼집 입구 피벗.
- 총 삼각형 117,894개. 분리된 메시 2개, 공유 재질 1개.
- Blender 기준 칼끝 +Z, 날 -X, 앞면 -Y.
- 4096×2048 Base Color, Roughness, Metallic, Normal 아틀라스.
- 노멀맵은 OpenGL 접선 공간 +Y. 표면 UV는 의도적으로 공유하며 별도 라이트맵 UV는 없습니다.

원본은 검과 칼집을 나란히 배치합니다. 칼집 위치를 `(0, 0, 0.140)`m로 옮기면 검을 덮는 위치가 됩니다. 칼집 내부는 빈 구조이며 날의 모든 버텍스가 내부 타원 단면 안에 들어가는지 검사합니다. 검과 칼집을 엔진에서 별도 오브젝트로 사용하고, 축과 단위를 대상 엔진에 맞게 설정하세요.

FBX 재질은 `Textures`의 이미지를 연결하세요. Base Color만 색상 텍스처로, 나머지는 데이터 텍스처로 사용합니다. Smoothness가 필요하면 1 − Roughness로 변환합니다.

## 검증 범위

검증 스크립트는 닫힌 메시, 퇴화 삼각형, 유한 좌표, UV·재질·원점을 확인합니다. GLB·FBX를 재가져와 각 오브젝트의 실제 버텍스 경계와 삼각형 수를 비교합니다. Blender 원본 재열기, 텍스처 패킹과 이전 무기 파일의 SHA-256 보존도 확인합니다. 실제 결과는 `Kokuren_validation.json`에 기록합니다.

사게오 끈은 정적 메시입니다. 골격, 천 물리, 자동 LOD, 충돌체와 공격 판정은 포함하지 않았습니다. 실제 게임 엔진의 렌더링·성능·발도 애니메이션은 검증하지 않았습니다.

## 재생성

다음 명령은 흑련 생성 파일을 덮어씁니다. 직접 편집한 결과는 다른 이름으로 보관하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python '.\scripts\build_kokuren.py'
```
