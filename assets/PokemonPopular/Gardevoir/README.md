# 가디안 · Gardevoir

공식 일러스트와 공식 Pokémon GO 렌더를 참고해 직접 구성한 정적 팬 모델입니다. 중앙이 뾰족한 녹색 앞머리, 각진 흰 얼굴과 붉은 눈, 긴 목과 팔, 앞뒤의 붉은 가슴 기관, 앞이 갈라진 흰 치마와 녹색 안쪽 형상을 중심으로 제작했습니다. 공식 게임 모델을 추출하거나 사용하지 않았습니다.

## 파일과 편집

- `Gardevoir.blend`: 편집 가능한 원본입니다. `Pokemon_Gardevoir`가 캐릭터, `90_Presentation`이 렌더 전용 배경입니다.
- `Gardevoir.glb`: 캐릭터만 내보낸 모델입니다.
- `renders/Gardevoir_preview.png`: 사선 대표 이미지입니다.
- `renders/Gardevoir_front.png`, `Gardevoir_back.png`, `Gardevoir_side.png`: 정면·후면·측면입니다.
- `renders/Gardevoir_face.png`, `Gardevoir_clay.png`: 얼굴 확대와 형상 확인용 클레이 이미지입니다.
- `renders/Gardevoir_glb_check.png`: 실제 GLB를 재임포트해 형태와 재질을 확인한 이미지입니다.
- `validation.json`: 원본 및 GLB 재임포트 검사 결과입니다. 통과 여부는 `passed`를 확인하세요.
- `delivery_check.json`: 원본·GLB 해시와 최종 6뷰·GLB 확인 이미지의 최신성 검사입니다.
- `Textures/Gardevoir_face.png`: 직접 그린 눈 텍스처입니다. Blender 원본과 GLB에 내장되어 있습니다.

`root_Gardevoir`를 이동·회전하면 모든 부위가 함께 움직입니다. 정면은 -Y, 위쪽은 +Z이며 발바닥은 Z=0입니다. 머리 끝까지 키는 약 1.6m입니다. 단색 PBR 재질과 패킹된 얼굴 텍스처를 사용하므로 모델을 여는 데 별도 텍스처 경로 설정이 필요하지 않습니다.

## 검사와 사용 범위

유한한 좌표, 퇴화 삼각형, 개별 메시의 경계·면 방향, UV와 재질, GLB 삼각형 수 및 실제 정점 경계를 검사합니다. GLB에서 UV·법선 경계 때문에 나뉜 정점은 0.0000001m 이내에서 용접한 뒤 경계를 검사합니다.

리깅·애니메이션·변형용 리토폴로지·게임 엔진 검증은 포함하지 않습니다. 여러 개의 닫힌 메시가 겹친 구조이므로 단일 수밀 메시나 3D 프린팅용 파일로 검증하지 않았습니다. 기본 UV는 단색 부품 재사용을 위한 투영이며 텍스처 페인팅용 아틀라스가 아닙니다.

## 재생성

프로젝트 루트에서 실행합니다. 직접 수정한 원본은 별도로 보관하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/popular_gardevoir.py
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/gardevoir_validate.py
```

빠른 확인은 첫 명령 뒤에 `-- --draft`, 모델과 GLB만 생성하려면 `-- --no-render`를 붙입니다. 공통 형상 도우미는 `scripts/popular_lucario.py`와 `scripts/pokemon_common.py`에서 가져옵니다.

## 참고

- [공식 도감](https://www.pokemon.com/us/pokedex/gardevoir)
- [공식 일러스트](https://assets.pokemon.com/assets/cms2/img/pokedex/full/282.png)
- [공식 Pokémon GO 렌더](https://www.pokemon.com/static-assets/content-assets/cms2/img/video-games/_tiles/pokemon-go/art/gardevoir.png)

원본 참고 이미지는 `references/`에 보관했으며 모델 텍스처로 사용하지 않았습니다. 캐릭터 디자인과 명칭의 권리는 해당 권리자에게 있습니다.
