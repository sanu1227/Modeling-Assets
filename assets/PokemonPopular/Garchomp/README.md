# 한카리아스 — Garchomp

공식 일러스트와 Pokémon HOME의 모습을 참고해 직접 만든 정적 포즈 팬 모델입니다. 상어처럼 뻗은 주둥이, 수평 머리 돌기, 붉은 목과 가슴, 황금색 무늬, 팔·등·꼬리의 지느러미와 낫 모양 손톱을 구성했습니다. 게임의 3D 메시를 추출하거나 사용하지 않았습니다.

## 파일

- [Garchomp.blend](Garchomp.blend): 편집 가능한 Blender 원본
- [Garchomp.glb](Garchomp.glb): 캐릭터만 포함하는 내장 텍스처 모델
- [대표 렌더](renders/preview.png) · [정면](renders/front.png) · [측면](renders/side.png) · [후면](renders/back.png) · [얼굴](renders/face.png) · [클레이](renders/clay.png)
- [검사 결과](validation.json): 저장한 원본과 GLB의 비교 결과
- [GLB 재임포트 렌더](renders/glb_reimport.png) · [재임포트 시각 검토](glb_visual_review.json) · [최종 렌더 해시·시점 확인](render_review.json)

`Pokemon_Garchomp` 컬렉션이 캐릭터입니다. `root_Garchomp`를 움직이면 모든 부품이 함께 움직입니다. `90_Presentation`의 받침대·조명·카메라는 GLB에 포함하지 않았습니다.

몸과 얼굴의 색상은 3072×3072 PNG, 뒤쪽 목과 발목 무늬는 2048×2048 PNG로 제작했으며 원본과 GLB에 내장했습니다. `Textures/`의 사본으로 무늬를 수정할 수 있습니다. 몸통·목·머리·사지·꼬리 중심부는 하나의 연속된 메시이고 지느러미·치아·발톱·가시는 별도 부품입니다.

## 검증과 범위

451,112개 삼각형을 검사했습니다. 유한한 정점 좌표, 극소 면적 삼각형, 부품별 닫힌 경계와 면 방향, UV·재질·패킹 이미지, GLB 삼각형 수와 실제 정점 경계 비교를 수행합니다. 실제 통과 여부와 파일 해시는 `validation.json`을 확인하세요.

전체 높이는 1.9m로 정규화했습니다. 정적 모델이며 리깅·애니메이션·변형용 리토폴로지·게임 엔진 동작·단일 수밀 3D 프린팅은 검증하지 않았습니다.

## 재생성

프로젝트 루트에서 실행합니다. 같은 이름의 생성 결과를 덮어쓰므로 직접 수정한 파일은 다른 이름으로 저장하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --threads 2 --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/popular_garchomp.py -- --draft
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/popular_garchomp.py -- --render-only --full --gpu
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/garchomp_validate.py
```

GPU가 없으면 렌더 명령에서 `--gpu`를 제외합니다.

참고: [공식 도감](https://www.pokemon.com/us/pokedex/garchomp), [공식 일러스트](https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/445.png), [일본 공식 소개](https://www.pokemon.jp/special/dragontype/lab/pokemon04.html). 포켓몬의 이름과 캐릭터 디자인에 대한 권리는 해당 권리자에게 있습니다.
