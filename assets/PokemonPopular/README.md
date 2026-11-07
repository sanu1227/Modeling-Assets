# 인기 포켓몬 팬 모델 컬렉션

원작의 실루엣·비율·색·표정을 참고해 직접 제작한 편집 가능한 Blender 팬 모델입니다. 신규 20종과 기존 리자몽을 합쳐 총 21종을 전시합니다. 공식 게임의 3D 메시를 추출한 자료가 아니며, 원작 모델과 동일한 메시를 재현했다고 보증하지 않습니다.

선정에는 [공식 Pokémon of the Year 2020 결과](https://pokemon2020.pokemon.com/en-us/)를 역사적 참고자료로 사용했습니다. 이 목록은 현재 인기 순위나 2026년 투표 결과가 아닙니다. 해당 투표의 상위권과 추가 대표 포켓몬을 함께 구성했습니다.

## 열기

프로젝트 루트의 [Open_Blender_Pokemon_Popular.cmd](../../Open_Blender_Pokemon_Popular.cmd)를 실행하면 포함된 Blender 5.2.3에서 [21종 전시 장면](Pokemon_Popular.blend)을 엽니다. 개별 수정에는 아래 각 포켓몬의 `.blend`를 사용하세요.

- [전시 배치 정보](gallery_manifest.json): 원본 경로·SHA-256·삼각형 수·전시 배율과 위치입니다.
- 전시 배치는 6열·4줄입니다. [전체 장면](renders/overview.png)과 행별 이미지 [1행](renders/row_01.png) · [2행](renders/row_02.png) · [3행](renders/row_03.png) · [4행](renders/row_04.png)을 확인할 수 있습니다.
- [전시 조립 스크립트](../../scripts/build_popular_gallery.py)와 [전체 검사 스크립트](../../scripts/verify_popular_catalog.py)를 함께 제공합니다.

전시 장면은 서로 보기 좋도록 모델별 높이를 정규화했습니다. 도감의 실제 신장이나 포켓몬 사이의 공식 크기 비율을 표현하지 않습니다. 개별 원본은 전시 장면의 배치·배율과 분리되어 있습니다.

## 모델 21종

표의 이미지는 각 모델의 최종 대표 뷰입니다. 정면·측면·후면·클레이 및 일부 얼굴 확대 뷰는 각 모델의 `renders/` 폴더에서 확인할 수 있습니다.

| 포켓몬 | 편집 원본 | 모델 GLB | 대표 이미지 |
|---|---|---|---|
| 개굴닌자 · Greninja | [blend](Greninja/Greninja.blend) | [glb](Greninja/Greninja.glb) | [보기](Greninja/renders/preview.png) |
| 루카리오 · Lucario | [blend](Lucario/Lucario.blend) | [glb](Lucario/Lucario.glb) | [보기](Lucario/renders/Lucario_preview.png) |
| 따라큐 · Mimikyu | [blend](Mimikyu/Mimikyu.blend) | [glb](Mimikyu/Mimikyu.glb) | [보기](Mimikyu/renders/hero.png) |
| 리자몽 · Charizard — 기존 보존 원본 | [blend](../Charizard/Charizard.blend) | [glb](../Charizard/Charizard.glb) | [보기](../Charizard/Charizard_preview.png) |
| 블래키 · Umbreon | [blend](Umbreon/Umbreon.blend) | [glb](Umbreon/Umbreon.glb) | [보기](Umbreon/renders/hero.png) |
| 님피아 · Sylveon | [blend](Sylveon/Sylveon.blend) | [glb](Sylveon/Sylveon.glb) | [보기](Sylveon/renders/hero.png) |
| 한카리아스 · Garchomp | [blend](Garchomp/Garchomp.blend) | [glb](Garchomp/Garchomp.glb) | [보기](Garchomp/renders/preview.png) |
| 레쿠쟈 · Rayquaza | [blend](Rayquaza/Rayquaza.blend) | [glb](Rayquaza/Rayquaza.glb) | [보기](Rayquaza/renders/hero.png) |
| 가디안 · Gardevoir | [blend](Gardevoir/Gardevoir.blend) | [glb](Gardevoir/Gardevoir.glb) | [보기](Gardevoir/renders/Gardevoir_preview.png) |
| 팬텀 · Gengar | [blend](Gengar/Gengar.blend) | [glb](Gengar/Gengar.glb) | [보기](Gengar/renders/hero.png) |
| 마기라스 · Tyranitar | [blend](Tyranitar/Tyranitar.blend) | [glb](Tyranitar/Tyranitar.glb) | [보기](Tyranitar/renders/Tyranitar_preview.png) |
| 루기아 · Lugia | [blend](Lugia/Lugia.blend) | [glb](Lugia/Lugia.glb) | [보기](Lugia/renders/preview.png) |
| 피카츄 · Pikachu | [blend](Pikachu/Pikachu.blend) | [glb](Pikachu/Pikachu.glb) | [보기](Pikachu/renders/hero.png) |
| 이브이 · Eevee | [blend](Eevee/Eevee.blend) | [glb](Eevee/Eevee.glb) | [보기](Eevee/renders/hero.png) |
| 렌트라 · Luxray | [blend](Luxray/Luxray.blend) | [glb](Luxray/Luxray.glb) | [보기](Luxray/renders/hero.png) |
| 누니머기 · Snom | [blend](Snom/Snom.blend) | [glb](Snom/Snom.glb) | [보기](Snom/renders/hero.png) |
| 망나뇽 · Dragonite | [blend](Dragonite/Dragonite.blend) | [glb](Dragonite/Dragonite.glb) | [보기](Dragonite/renders/hero.png) |
| 뮤츠 · Mewtwo | [blend](Mewtwo/Mewtwo.blend) | [glb](Mewtwo/Mewtwo.glb) | [보기](Mewtwo/renders/hero.png) |
| 잠만보 · Snorlax | [blend](Snorlax/Snorlax.blend) | [glb](Snorlax/Snorlax.glb) | [보기](Snorlax/renders/hero.png) |
| 뮤 · Mew | [blend](Mew/Mew.blend) | [glb](Mew/Mew.glb) | [보기](Mew/renders/hero.png) |
| 샹델라 · Chandelure | [blend](Chandelure/Chandelure.blend) | [glb](Chandelure/Chandelure.glb) | [보기](Chandelure/renders/hero.png) |

## 파일 구성과 사용 범위

신규 모델의 캐릭터는 `Pokemon_영문이름` 컬렉션, 촬영 장치는 `90_Presentation` 컬렉션에 있습니다. GLB에는 캐릭터만 내보내며 조명·카메라·전시 받침대는 제외합니다. 텍스처를 사용하는 모델은 필요한 이미지를 `.blend`와 `.glb`에 내장하고, 수정용 PNG도 모델 폴더 또는 그 아래 `Textures/` 폴더에 보관합니다. 단색 재질 모델에는 별도 이미지가 필요하지 않습니다.

따라큐의 Blender 재질에는 3D 절차적 노이즈를 이용한 미세한 천 표면 bump가 있습니다. 이 bump는 GLB로 내보내지지 않으므로 GLB 표면이 더 매끈하게 보입니다. 색 텍스처와 기본 거칠기는 GLB에 포함합니다.

모두 정적 포즈입니다. 리깅·애니메이션·변형용 리토폴로지·LOD·충돌체는 포함하지 않습니다. Blender 렌더 및 GLB 재임포트는 확인하지만 게임 엔진의 실행·성능은 별도로 검증하지 않았습니다. 닫힌 부품들이 서로 겹치는 구성도 있으므로 단일 수밀 3D 프린팅 모델로 보증하지 않습니다.

이번 이브이는 `PokemonPopular/Eevee/`에 새로 제작했으며 기존 스타팅 장면을 대체하지 않습니다. 기존 파일의 보존 검사 결과와 예외는 아래에 기록했습니다. 생성 스크립트를 실행하면 해당 신규 모델 결과를 덮어쓰므로 수동 수정본은 다른 이름으로 저장하세요. 모델별 재생성 명령은 각 폴더의 README에 있습니다.

## 검증 상태

개별 `validation.json`은 저장한 Blender 원본과 GLB를 다시 열어 검사한 결과입니다. 정점 좌표의 유한성, UV 존재 여부, 극소 면적 삼각형, 부품별 경계·면 방향, 재질·이미지 내장, GLB 삼각형 수와 정점 경계를 확인합니다. 구체적인 허용오차와 결과는 각 보고서를 확인하세요. 렌더를 통한 원작 비교는 수치 검사와 별도로 수행합니다.

기존 `Charizard`와 `PokemonStarters` 파일은 [preserved_assets.json](preserved_assets.json)에 기록한 기준 SHA-256과 일치합니다. `Buizel.blend`와 `Buizel.glb`는 13:14 기준 해시와 다릅니다. 별도 `build_buizel.py` 작업이 13:17:50에 파일을 갱신하고 13:19에 완료한 기록이 있어, 현재 완성본을 유지합니다. 모든 기존 파일이 시작 시점과 동일하다고 판정하지 않습니다. 전체 보고서에는 이 차이를 경고로 남기며 `previous_assets_unchanged=false`를 유지합니다.

**최종 통합 검사 완료:** 2026년 11월 4일 15:29 KST 기준 [catalog_validation.json](catalog_validation.json)의 `passed=true`, `errors=[]`를 확인했습니다. 신규 20종의 원본·GLB 검사, 최신 렌더와 원본 해시 일치, 21종 전시 원본 검사를 통과했습니다. 기존 브이젤의 기록된 빌드 변경 2건은 별도 경고로 유지합니다.

## 참고자료

- **공식 2D 원화:** Pokémon.com의 도감과 [공식 CDN 일러스트 예시 — 이브이](https://assets.pokemon.com/assets/cms2/img/pokedex/full/133.png)를 형태·색의 기본 기준으로 사용했습니다. 개별 모델의 `references/`와 README에 해당 출처가 있습니다.
- **HOME 모습 보조자료:** [PokeAPI sprites 저장소의 HOME 이미지](https://github.com/PokeAPI/sprites/tree/master/sprites/pokemon/other/home)는 입체 비율과 측면 형태를 비교하는 보조 미러입니다. 이 GitHub 저장소를 Pokémon의 공식 배포처로 표시하지 않습니다.
- **역사적 선정 참고:** [Pokémon of the Year 2020](https://pokemon2020.pokemon.com/en-us/). 전시 메타데이터의 `vote_2020_rank`는 이 당시 결과이며, 값이 없는 모델도 함께 전시합니다.

포켓몬 이름과 원작 캐릭터 디자인의 권리는 해당 권리자에게 있습니다. 이 컬렉션은 원작을 참고한 팬 제작물입니다.
