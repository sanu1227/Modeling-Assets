# 포켓몬 스타팅 컬렉션

공식 일러스트의 비율, 실루엣, 색상과 주요 특징을 참고해 직접 구성한 정적 3D 팬 모델입니다. 공식 게임의 3D 에셋을 추출하거나 사용하지 않았습니다.

## 구성

- 1~9세대 풀·불꽃·물 기본형 27종
- 특별 파트너 피카츄·이브이 2종
- 2027년 발매 예정 『포켓몬스터 윈드·웨이브』 공개 기본형 초로삐·포뭉이·미초리 3종

총 32종입니다. 진화형은 포함하지 않습니다. 캐릭터는 전시를 위해 개별 크기를 정규화했으며 도감의 실제 키 비율을 적용하지 않았습니다.

## 파일 열기

- `../../Open_Blender_Pokemon_Starters.cmd`: Blender에서 전체 장면 열기
- `Pokemon_Starters.blend`: 컬렉션과 부위별로 편집 가능한 원본
- `models/<영문 이름>.glb`: 캐릭터만 포함하는 개별 모델 32개. 원점은 바닥 중앙입니다.
- `renders/`: 세대별 사선 뷰, 전체 장면, 정면 방향 전체 뷰, 클레이 렌더
- `renders/Pokemon_Starters_Catalog.png`: 32종을 세대별로 정리한 전체 미리보기
- `roster.json`: 한글·영문 이름, 도감번호, 세대와 파일 경로
- `validation.json`: 원본 메시와 개별 GLB 재임포트 검사 결과

Blender Outliner에서 `Pokemon_Bulbasaur`처럼 `Pokemon_`으로 시작하는 컬렉션을 선택합니다. 해당 컬렉션의 `root_Bulbasaur`를 이동·회전하면 부품이 함께 움직입니다. `Display_`는 받침대와 이름표, `90_Presentation`은 조명·카메라·배경입니다. 개별 GLB에는 전시용 요소가 없습니다.

## 제작 및 검증

Blender 5.2.3에서 제작했습니다. 얼굴, 무늬, 털, 잎, 불꽃, 지느러미는 편집 가능한 입체 메시로 구성했습니다. 단색 PBR 재질을 사용해 외부 텍스처 없이 열 수 있습니다.

검사 항목: 유한한 정점 좌표, 면적이 0에 가까운 삼각형, 메시 구성요소별 경계와 면 방향, 재질, GLB 삼각형 수와 경계 일치, 전시용 요소의 내보내기 제외. 세부 결과와 실제 통과 여부는 `validation.json`을 확인하세요.

리깅·애니메이션·변형용 리토폴로지·게임 엔진 실행 검증은 포함하지 않습니다. 여러 폐쇄 메시가 겹쳐 구성된 모델이므로 단일 수밀 메시나 3D 프린팅용 파일로 검증하지 않았습니다. 원작을 참고한 해석 모델로, 공식 모델과 동일한 형상을 보증하지 않습니다.

## 재생성

프로젝트 루트 PowerShell에서 실행합니다. 재생성 명령은 이 컬렉션의 생성 결과를 덮어쓰므로 직접 수정한 원본은 별도 파일로 저장하세요.

```powershell
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/build_pokemon_starters.py
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/build_pokemon_starters.py -- --render all
& '.\tools\blender-5.2.3-windows-x64\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/verify_pokemon_starters.py
```

특정 모델만 다시 만들려면 `-- --rebuild Bulbasaur,Charmander`를 사용합니다. 변경 후 관련 렌더와 검증을 다시 실행해야 합니다.

## 참고 자료

- [포켓몬 공식 도감](https://www.pokemon.com/us/pokedex): 1~9세대 기본형과 특별 파트너 일러스트
- [윈드·웨이브 한국 공식](https://pokemonkorea.co.kr/winds_waves/menu724): 신작 기본형 한국 이름
- [윈드·웨이브 공식](https://windswaves.pokemon.com/en-us/): 신작 기본형 일러스트 및 공개 정보
- [레츠고 공식](https://pokemonletsgo.pokemon.com/en-us/): 피카츄·이브이 파트너 구분

참고 이미지는 `references/`에 있으며 모델 텍스처로 사용하지 않았습니다. 포켓몬 이름과 원작 캐릭터 디자인의 권리는 해당 권리자에게 있습니다.
