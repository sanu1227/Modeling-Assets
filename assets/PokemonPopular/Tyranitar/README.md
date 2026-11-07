# 마기라스 · Tyranitar

공식 일러스트를 기준으로 직접 구성한 정적 팬 모델입니다. 두꺼운 몸통과 꼬리, 열린 입과 네 개의 송곳니, 작은 눈, 머리의 세 돌기, 다섯 쌍의 등 갑옷, 손발의 세 발톱, 검은 무늬와 파란 배판을 재현했습니다. 공식 게임 모델을 추출하거나 사용하지 않았습니다.

## 파일

- `Tyranitar.blend`: 부위별로 편집할 수 있는 원본입니다.
- `Tyranitar.glb`: 캐릭터만 내보낸 모델입니다.
- `renders/Tyranitar_preview.png`: 사선 대표 이미지입니다.
- `renders/Tyranitar_front.png`, `Tyranitar_back.png`, `Tyranitar_side.png`: 정면·후면·측면입니다.
- `renders/Tyranitar_face.png`, `Tyranitar_clay.png`: 얼굴 확대와 형상 확인용 클레이 렌더입니다.
- `renders/Tyranitar_glb_check.png`: 실제 GLB를 재임포트해 형태와 재질을 확인한 이미지입니다.
- `Textures/`: 직접 그린 몸통·얼굴·양쪽 허벅지 무늬입니다. Blender 원본과 GLB에 내장됩니다.
- `validation.json`: 원본과 GLB 재임포트 검사 결과입니다. 통과 여부는 `passed`를 확인하세요.
- `delivery_check.json`: 원본·GLB 해시와 최종 6뷰·GLB 확인 이미지의 최신성 검사입니다.

`Pokemon_Tyranitar` 컬렉션이 캐릭터이며 `root_Tyranitar`로 전체를 움직입니다. `90_Presentation`은 배경·조명·카메라·받침대이며 GLB에서 제외합니다. 정면은 -Y, 위쪽은 +Z, 발바닥은 Z=0입니다. 머리 돌기 끝까지 키를 약 2.0m에 맞췄습니다.

## 검사와 사용 범위

유한한 좌표, 퇴화 삼각형, 닫힌 개별 메시의 경계·면 방향, UV, 재질, 이미지 패킹, GLB 삼각형 수와 실제 정점 경계를 검사합니다. GLB의 UV·법선 경계에서 분리된 정점은 0.0000001m 이내에서 용접한 뒤 경계를 검사합니다.

여러 개의 닫힌 메시가 겹치는 구조입니다. 리깅·애니메이션·변형용 리토폴로지·게임 엔진 실행이나 단일 수밀 3D 프린팅 파일로 검증하지 않았습니다. 단색 부품에는 재사용을 위한 기본 투영 UV가 있습니다.

## 재생성

프로젝트 루트에서 실행합니다. 직접 수정한 원본은 별도로 저장하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/popular_tyranitar.py
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/tyranitar_validate.py
```

빠른 정면·사선 확인은 첫 명령 뒤에 `-- --draft`를 붙입니다. `-- --no-render`는 모델과 GLB만 생성합니다. 저장된 원본의 GPU 렌더는 `scripts/lucario_render_gpu.py -- Tyranitar`로 실행할 수 있습니다. 공통 형상 도우미는 `scripts/popular_lucario.py`와 `scripts/pokemon_common.py`를 사용합니다.

## 참고

- [공식 도감](https://www.pokemon.com/us/pokedex/tyranitar)
- [공식 일러스트](https://assets.pokemon.com/assets/cms2/img/pokedex/full/248.png)
- [공식 라이선스 Jazwares 피규어 후면](https://www.argos.co.uk/product/7789283): 두 줄의 등 돌기와 뒤쪽 무늬 확인에 사용했습니다. 장난감의 버튼·관절·나사는 재현하지 않았습니다.

참고 이미지는 `references/`에 보관했고 모델 텍스처로 사용하지 않았습니다. 캐릭터 디자인과 명칭의 권리는 해당 권리자에게 있습니다.
