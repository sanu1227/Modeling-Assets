# 루기아 — Lugia

공식 일러스트와 Pokémon GO 공식 이미지를 참고해 직접 만든 정적 포즈 팬 모델입니다. 긴 목과 물새 형태의 머리, 파란 눈가 돌기, 다섯 갈래 손날개, 다섯 쌍의 등 지느러미, 긴 꼬리의 파란 가시 두 개를 구성했습니다. 게임의 3D 메시를 추출하거나 사용하지 않았습니다.

## 파일

- [Lugia.blend](Lugia.blend): 편집 가능한 Blender 원본
- [Lugia.glb](Lugia.glb): 캐릭터만 포함하는 내장 텍스처 모델
- [대표 렌더](renders/preview.png) · [정면](renders/front.png) · [측면](renders/side.png) · [후면](renders/back.png) · [얼굴](renders/face.png) · [클레이](renders/clay.png)
- [검사 결과](validation.json): 저장한 원본과 GLB의 비교 결과
- [GLB 재임포트 렌더](renders/glb_reimport.png) · [재임포트 시각 검토](glb_visual_review.json) · [최종 렌더 해시·시점 확인](render_review.json)

`Pokemon_Lugia` 컬렉션이 캐릭터입니다. `root_Lugia`를 움직이면 모든 부품이 함께 움직입니다. `90_Presentation`의 받침대·조명·카메라는 GLB에 포함하지 않았습니다. 정면은 -Y, 위쪽은 Z이며 발바닥은 Z=0에 맞췄습니다.

몸통·목·날개·다리·꼬리는 하나의 연속된 메시입니다. 손날개에는 손끝의 둥근 모서리, 앞쪽으로 굽힌 마디, 손바닥의 부피와 비틀림을 넣었습니다. 머리·눈가 돌기·지느러미·입 안의 부품은 별도로 편집할 수 있습니다.

배 무늬는 3072×3072 PNG, 얼굴은 2048×2048 PNG로 제작했으며 원본과 GLB에 내장했습니다. `Textures/`의 사본으로 무늬를 수정할 수 있습니다.

## 검증과 범위

603,192개 삼각형을 검사했습니다. 유한한 정점 좌표, 극소 면적 삼각형, 부품별 닫힌 경계와 면 방향, UV·재질·패킹 이미지, GLB 삼각형 수와 실제 정점 경계 비교를 수행합니다. 등 지느러미 10개와 꼬리 가시 2개도 확인합니다. 실제 통과 여부와 파일 해시는 `validation.json`을 확인하세요.

날개 끝을 포함한 포즈 전체 높이를 5.2m로 정규화했습니다. 이 값은 해부학적 직립 키를 뜻하지 않습니다. 정적 모델이며 리깅·애니메이션·변형용 리토폴로지·게임 엔진 동작·단일 수밀 3D 프린팅은 검증하지 않았습니다.

## 재생성

프로젝트 루트에서 실행합니다. 같은 이름의 생성 결과를 덮어쓰므로 직접 수정한 파일은 다른 이름으로 저장하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --threads 2 --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/popular_lugia.py -- --draft --full
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/popular_lugia.py -- --render-only --full --gpu
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/lugia_validate.py
```

GPU가 없으면 렌더 명령에서 `--gpu`를 제외합니다.

참고: [공식 도감](https://www.pokemon.com/us/pokedex/lugia), [공식 일러스트](https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/249.png), [Pokémon GO 공식 이미지](https://www.pokemon.com/static-assets/content-assets/cms2/img/video-games/_tiles/pokemon-go/art/lugia.png). 포켓몬의 이름과 캐릭터 디자인에 대한 권리는 해당 권리자에게 있습니다.
