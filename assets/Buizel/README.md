# 브이젤 3D 모델

공식 일러스트와 게임형 참고 이미지를 보고 Blender 5.2.3에서 직접 구성한 정적 팬 모델입니다. 주황 몸체, 크림색 얼굴·배 무늬, 노란 부낭, 파란 팔 지느러미와 크림색 끝을 가진 두 꼬리를 포함합니다. 등 무늬가 두 개인 수컷 형태이며, 전체 높이는 공식 도감의 0.7m에 맞췄습니다.

원작 형태를 해석하여 제작한 모델입니다. 공식 게임 메시를 추출한 에셋이나 공식 모델과 동일한 형상은 아닙니다.

## 열기와 편집

- [Blender로 열기](../../Open_Blender_Buizel.cmd)
- [Buizel.blend](Buizel.blend): 부위별 편집이 가능한 원본입니다.
- [Buizel.glb](Buizel.glb): 캐릭터와 내장 재질·텍스처를 포함합니다. 받침대·배경·조명·카메라는 제외했습니다.
- `Buizel` 컬렉션의 `Buizel • move whole character`를 선택하면 캐릭터 전체를 이동할 수 있습니다. `90_Presentation`은 전시용 요소입니다.
- 얼굴·몸체는 각각 2048×2048, 꼬리 끝은 512×1024 UV 텍스처를 사용합니다. 이미지 3개는 `.blend`에 패킹되어 있고 GLB에도 내장되어 있습니다. 원본 PNG는 [Textures](Textures/)에 있습니다.

## 미리보기

[대표 이미지](Buizel_preview.png) · [정면](Buizel_front.png) · [측면](Buizel_side.png) · [후면](Buizel_back.png) · [얼굴 확대](Buizel_face.png) · [클레이](Buizel_clay.png)

## 최종 검증

2026-11-04 최종 `.blend`를 다시 열고 GLB를 재임포트했습니다. [Buizel_validation.json](Buizel_validation.json)의 `passed`는 `true`이며, 전체 실행 로그는 [buizel_verify.log](../../logs/buizel_verify.log)에 있습니다.

- 메시 18개, 재질 9개, 삼각형 568,080개입니다. 원본과 재임포트 GLB의 삼각형 수가 일치합니다.
- 크기는 약 0.357344 × 0.564274 × 0.700000m입니다. 원본과 GLB의 정점 경계 차이는 0m입니다.
- 비정상 좌표·퇴화 삼각형·누락 재질이 없습니다. 이미지 재질에 필요한 UV 존재 여부, 이미지 패킹, GLB 이미지 내장과 전시용 요소 제외 검사를 통과했습니다.
- 원본 비다양체 모서리는 0개입니다. GLB 재임포트에서는 분리된 정점 경계 1,592개가 보고됩니다.
- 기존 `Charizard.blend`와 `Charizard.glb`는 제작 전 [SHA-256 기록](preserved_assets.json)과 일치합니다.

고밀도 정적 모델이며 리깅·애니메이션은 포함하지 않습니다. 실시간 게임 성능이나 엔진 동작은 검증하지 않았습니다. 일부 부품이 겹치는 구성으로, 단일 수밀 메시나 3D 프린팅용 파일로 검증하지 않았습니다.

## 재생성

[제작 스크립트](../../scripts/build_buizel.py)와 [검증 스크립트](../../scripts/verify_buizel.py)를 제공합니다. 재생성은 이 폴더의 결과 파일을 덮어쓰므로 직접 수정한 작업은 다른 이름으로 저장하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python '.\scripts\build_buizel.py'
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --python-exit-code 1 --python '.\scripts\verify_buizel.py'
```

## 참고 자료

- [포켓몬 공식 브이젤 도감](https://in.portal-pokemon.com/pokedex/0418/): 캐릭터 형태와 공식 높이 0.7m. [저장한 공식 이미지](reference/Buizel_official.png)
- [Pokémon Database artwork](https://pokemondb.net/artwork/buizel): [기본 일러스트](reference/Buizel_classic.jpg), [벡터 일러스트](reference/Buizel_vector.png)
- 게임·HOME형 참고 이미지: [게임형](reference/Buizel_game.png), [후면](reference/Buizel_back.png). 형태 확인용이며 모델 텍스처로 사용하지 않았습니다.
