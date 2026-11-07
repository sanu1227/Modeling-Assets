# 루카리오 · Lucario

공식 포켓몬 일러스트를 참고해 직접 구성한 정적 3D 팬 모델입니다. 긴 삼각형 귀, 검정 얼굴 무늬와 붉은 눈, 돌출된 주둥이, 네 개의 파동 감지 부위, 가슴·손등 가시, 파란 허벅지와 검정 종아리의 비율을 기준으로 제작했습니다. 공식 게임 메시를 추출하거나 사용하지 않았습니다.

## 파일

- `Lucario.blend`: 부위별로 편집할 수 있는 Blender 원본입니다.
- `Lucario.glb`: 캐릭터만 내보낸 모델입니다. 배경·받침대·조명·카메라는 제외합니다.
- `renders/Lucario_preview.png`: 사선 대표 이미지입니다.
- `renders/Lucario_front.png`, `Lucario_back.png`, `Lucario_side.png`: 정면·후면·측면입니다.
- `renders/Lucario_face.png`, `Lucario_clay.png`: 얼굴 확대와 형상 확인용 클레이 렌더입니다.
- `renders/Lucario_glb_check.png`: 실제 GLB를 재임포트해 형태와 재질을 확인한 이미지입니다.
- `Textures/Lucario_face_markings.png`: 직접 그린 얼굴 색상 무늬입니다. `.blend`에 패킹되어 있고 GLB에도 내장됩니다.
- `validation.json`: 원본과 GLB 재임포트 검사 결과입니다. 최종 통과 여부는 `passed`를 확인하세요.
- `delivery_check.json`: 원본·GLB 해시와 최종 6뷰·GLB 확인 이미지의 최신성 검사입니다.

`Pokemon_Lucario` 컬렉션이 캐릭터입니다. `root_Lucario`를 이동·회전하면 모든 부위가 함께 움직입니다. `90_Presentation`은 렌더 전용 요소입니다. 정면은 -Y, 위쪽은 +Z이며, 발바닥 높이는 Z=0입니다. 귀 끝을 포함한 키를 도감상 키인 약 1.2m에 맞췄습니다.

## 검사와 사용 범위

유한한 정점, 퇴화 삼각형, 닫힌 개별 메시의 경계·면 방향, UV, 재질, 이미지 패킹, GLB 삼각형 수 및 실제 정점 경계를 검사합니다. GLB의 UV와 법선 경계에서 나뉜 정점은 비교 시 0.0000001m 이내에서 용접해 메시 경계를 검사합니다.

리깅·애니메이션·변형용 리토폴로지·게임 엔진 실행 검증은 포함하지 않습니다. 몸과 장식은 여러 개의 닫힌 메시가 겹친 구조입니다. 단일 수밀 메시나 3D 프린팅용 파일로 검증하지 않았습니다. 단색 부품의 UV는 재사용을 위한 기본 투영이며, 텍스처 페인팅용으로 펼친 UV 아틀라스가 아닙니다.

## 재생성

프로젝트 루트에서 다음 명령을 실행합니다. 재생성은 이 폴더의 생성물을 덮어쓰므로 직접 수정한 원본은 별도 이름으로 저장하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/popular_lucario.py
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/lucario_validate.py
```

빠른 정면·사선 확인은 첫 명령 뒤에 `-- --draft`를 붙입니다. 모델·GLB만 생성하려면 `-- --no-render`를 사용합니다.

## 참고

- [공식 포켓몬 도감](https://www.pokemon.com/us/pokedex/lucario)
- [공식 일러스트](https://assets.pokemon.com/assets/cms2/img/pokedex/full/448.png)
- [공식 라이선스 Jazwares 피규어 후면 사진](https://www.gucca.dk/pokmon-battle-figure-lucario-p760305): 뒤쪽 네 개의 감지 부위와 몸 색상 확인에만 사용했습니다.

참고 이미지는 `references/`에 보관했으며 모델 텍스처에 사용하지 않았습니다. 포켓몬 캐릭터 디자인과 명칭의 권리는 해당 권리자에게 있습니다.
