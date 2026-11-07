# 개굴닌자 — Greninja

공식 일러스트와 설정화, Pokémon HOME의 모습을 참고해 직접 만든 정적 포즈 팬 모델입니다. 머리 지느러미, 삼각형 눈, 혀 스카프, 큰 개구리 허벅지와 물갈퀴를 원작의 실루엣에 맞춰 구성했습니다. 게임의 3D 메시를 추출하거나 사용하지 않았습니다.

## 파일

- [Greninja.blend](Greninja.blend): 편집 가능한 Blender 원본
- [Greninja.glb](Greninja.glb): 캐릭터만 포함하는 내장 텍스처 모델
- [대표 렌더](renders/preview.png) · [정면](renders/front.png) · [측면](renders/side.png) · [후면](renders/back.png) · [얼굴](renders/face.png) · [클레이](renders/clay.png)
- [검사 결과](validation.json): 저장한 원본과 GLB를 다시 열어 비교한 결과
- [GLB 재임포트 렌더](renders/glb_reimport.png) · [재임포트 시각 검토](glb_visual_review.json) · [최종 렌더 해시·시점 확인](render_review.json)

`Pokemon_Greninja` 컬렉션이 캐릭터입니다. `root_Greninja`를 움직이면 모든 부품이 함께 움직입니다. `90_Presentation`의 받침대·조명·카메라는 GLB에 포함하지 않았습니다.

머리와 엉덩이의 무늬는 각각 2048×2048 PNG로 제작했으며 원본과 GLB에 내장했습니다. `Textures/`의 사본으로 색과 무늬를 수정할 수 있습니다. 몸통과 사지는 연속된 메시이며 머리, 지느러미, 혀, 흰 반점과 손발의 패드는 별도 부품입니다.

## 검증과 범위

391,918개 삼각형을 검사했습니다. 유한한 정점 좌표, 극소 면적 삼각형, 부품별 닫힌 경계와 면 방향, UV·재질·패킹 이미지, GLB 삼각형 수와 실제 정점 경계 비교를 수행합니다. 실제 통과 여부와 파일 해시는 `validation.json`을 확인하세요.

전시를 위해 웅크린 자세 전체 높이를 1.5m로 정규화했습니다. 도감의 신장을 포즈에 맞춰 엄밀히 환산한 값은 아닙니다. 정적 모델이며 리깅·애니메이션·변형용 리토폴로지·게임 엔진 동작·단일 수밀 3D 프린팅은 검증하지 않았습니다.

## 재생성

프로젝트 루트에서 실행합니다. 같은 이름의 생성 결과를 덮어쓰므로 직접 수정한 파일은 다른 이름으로 저장하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --threads 2 --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/popular_greninja.py -- --draft
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/popular_greninja.py -- --render-only --full --gpu
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/greninja_validate.py
```

GPU가 없으면 렌더 명령에서 `--gpu`를 제외합니다.

참고: [공식 도감](https://www.pokemon.com/us/pokedex/greninja), [공식 일러스트](https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/658.png), [설정화 보관본](https://www.pokewiki.de/images/e/e3/Quajutsu_Konzeptzeichnung.png). 포켓몬의 이름과 캐릭터 디자인에 대한 권리는 해당 권리자에게 있습니다.
