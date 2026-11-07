# 팬텀 — Gengar

공식 일러스트를 참고해 직접 제작한 정적 포즈 팬 모델입니다. 주요 형태 기준은 큰 미소와 붉은 눈, 등과 머리의 가시 실루엣입니다. 공식 게임의 3D 메시를 추출하거나 가져오지 않았습니다.

## 파일

- [Gengar.blend](Gengar.blend): 편집 가능한 Blender 원본입니다.
- [Gengar.glb](Gengar.glb): 캐릭터만 포함하는 GLB입니다.
- [렌더 폴더](renders/): `hero.png`, `front.png`, `side.png`, `back.png`, `clay.png`가 최종 뷰이며, `_draft` 파일은 작업 중 초안입니다.
- [검증 보고서](validation.json): 저장한 원본과 GLB를 다시 열어 비교한 결과입니다.
- [참고 원화](references/official.png): 모델링에 사용한 공식 일러스트 사본입니다.

캐릭터는 `Pokemon_Gengar`, 촬영 장치는 `90_Presentation` 컬렉션에 있습니다. GLB에는 촬영 장치를 넣지 않았습니다. 모델 앞쪽은 -Y, 위쪽은 +Z입니다. 수정용 색 텍스처는 [Gengar_face.png](Gengar_face.png)입니다. 필요한 이미지는 Blender 원본과 GLB에 내장합니다.

## 검증과 범위

정점 좌표, 극소 면적 삼각형, 부품별 닫힌 경계·면 방향, UV·재질과 GLB 삼각형 수·실제 정점 경계를 검사합니다. 최신 통과 여부는 `validation.json`을 확인하세요. 최종 이미지의 원본 일치 여부는 전체 작업 후 상위 폴더의 `catalog_validation.json`에서 판정합니다.

정적 모델이며 리깅·애니메이션·게임 엔진 실행·변형용 리토폴로지는 포함하지 않습니다. 여러 폐쇄 부품이 겹칠 수 있어 단일 수밀 3D 프린팅 모델로 검증하지 않았습니다. 전체 전시에서는 모델별 높이를 정규화하므로 공식 신장 비율과 다릅니다.

## 재생성

프로젝트 루트에서 실행합니다. 생성 스크립트는 이 폴더의 원본과 GLB를 덮어쓰므로 직접 수정한 작업은 다른 이름으로 저장하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python scripts/popular_gengar.py -- --build-only
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python scripts/popular_render.py -- --name Gengar --gpu
```

첫 명령은 원본 생성·GLB 내보내기·재임포트 검사를 수행합니다. 두 번째 명령은 저장된 원본의 최종 5뷰를 렌더하고 원본 해시를 기록합니다. NVIDIA OptiX를 사용하지 않는 환경에서는 두 번째 명령의 `--gpu`를 제외하세요.

## 참고

- [공식 도감](https://www.pokemon.com/us/pokedex/gengar)
- [공식 일러스트](https://assets.pokemon.com/assets/cms2/img/pokedex/full/094.png)

원작 이름과 캐릭터 디자인의 권리는 해당 권리자에게 있습니다. 이 모델은 원작을 참고한 팬 제작물입니다.
