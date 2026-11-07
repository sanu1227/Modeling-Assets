# 블래키 — Umbreon

공식 일러스트와 Pokémon HOME 렌더의 체형·색·표정을 참고해 직접 작성한 정적 3D 팬 모델입니다. 외부 3D 메시를 가져오지 않았습니다.

- `Umbreon.blend`: 부위별로 편집 가능한 Blender 원본입니다. 캐릭터는 `Pokemon_Umbreon`, 촬영 장치는 `90_Presentation` 컬렉션에 있습니다.
- `Umbreon.glb`: 캐릭터만 포함합니다. 받침대, 조명, 카메라는 제외했습니다.
- `renders/hero.png`: 대표 사선 뷰입니다. `front.png`, `side.png`, `back.png`, `clay.png`도 함께 확인할 수 있습니다.
- `validation.json`: 저장한 원본을 다시 열고 GLB를 재임포트하여 확인한 결과입니다.
- [GLB 재임포트 렌더](renders/glb_reimport.png)와 [원본·GLB 해시 기록](glb_visual_review.json): 내보낸 파일을 새로 불러와 만든 실제 확인 이미지입니다. 원본 파일은 바꾸지 않습니다.

모델 앞쪽은 -Y, 위쪽은 +Z이며 원점은 바닥 중앙입니다. 공식 도감의 키로 정규화하지 않은 전시용 크기입니다. 단색 재질과 표면 UV를 사용하며 외부 텍스처가 필요하지 않습니다. 귀와 꼬리의 금색 띠는 표면 재질로, 이마와 다리의 금색 고리는 곡면을 따라 배치한 편집 가능한 메시로 구성했습니다.

리깅·애니메이션·게임 엔진 실행은 포함하지 않습니다. 여러 폐쇄 메시가 겹친 구성으로, 단일 수밀 3D 프린팅 모델로 검증하지 않았습니다. 원작 디자인의 권리는 해당 권리자에게 있습니다.

## 재생성

프로젝트 루트에서 다음 명령을 실행합니다. 이 폴더의 생성 파일을 덮어쓰므로 직접 수정한 작업은 다른 이름으로 보관하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/popular_umbreon.py -- --all
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/eeveelutions_verify.py -- Umbreon
```

## 참고

- [공식 도감](https://www.pokemon.com/us/pokedex/umbreon)
- [공식 일러스트](https://assets.pokemon.com/assets/cms2/img/pokedex/full/197.png)
- [Pokémon HOME 렌더 미러 — PokeAPI](https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/197.png)

참고 이미지는 `references/`에 보관했습니다. 모델 텍스처로 사용하지 않았습니다.
