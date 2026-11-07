# 리자몽 3D 모델

Blender 5.2.3에서 제작한 정적 포즈의 리자몽 팬 모델입니다. 날개, 발톱, 꼬리 불꽃과 눈 텍스처를 포함합니다. 외부 메시를 가져오지 않고 Blender 스크립트로 형상을 만들었습니다.

## 열기와 수정

- [Blender 실행](../../Open_Blender_Charizard.cmd): 편집 가능한 [Charizard.blend](Charizard.blend)를 엽니다.
- `Charizard` 컬렉션: 캐릭터 모델입니다. 부품별 선택과 편집이 가능합니다.
- `90_Presentation` 컬렉션: 받침대, 배경, 조명과 카메라입니다.
- [Charizard.glb](Charizard.glb): 캐릭터만 내보낸 파일입니다. 스튜디오와 받침대는 제외합니다.
- 대부분 단색 PBR 재질이며, 눈은 [Textures/Charizard_eyes.png](Textures/Charizard_eyes.png)를 사용합니다. 1024×512 눈 이미지는 `.blend`에 패킹되어 있고 GLB에도 내장되어 있습니다.

## 미리보기

- [대표 이미지](Charizard_preview.png)
- [정면](Charizard_front.png) · [후면](Charizard_back.png) · [얼굴](Charizard_face.png) · [클레이](Charizard_clay.png)

## 검증 결과

2026-11-04, 저장한 `.blend`를 다시 열고 GLB를 재임포트하여 검사했습니다. [Charizard_validation.json](Charizard_validation.json)의 `passed`는 `true`입니다.

- 메시 52개, 재질 9개, 평가된 삼각형 319,768개입니다. 원본과 GLB의 삼각형 수가 같습니다.
- 전체 크기는 약 2.372 × 1.113 × 1.646m이며, 원본과 재임포트 모델의 경계 차이는 0m입니다.
- 비정상 좌표, 퇴화 삼각형, 누락 재질이 없습니다. 눈 이미지 패킹, GLB 이미지 내장, 카메라·조명 제외 검사를 통과했습니다.
- 원본 부품의 비다양체 모서리는 0개입니다. GLB 재임포트에서는 분리된 정점 경계가 포함되어 비다양체 모서리 684개가 보고됩니다.

리깅과 애니메이션이 없는 고밀도 정적 모델입니다. 게임 엔진 동작이나 실시간 성능은 검증하지 않았습니다. 별개 부품들이 겹치는 구조이며, 3D 프린팅용으로 합쳐진 단일 수밀 표면이 아닙니다.

재생성 스크립트는 [build_charizard.py](../../scripts/build_charizard.py), 검증 스크립트는 [verify_charizard.py](../../scripts/verify_charizard.py)입니다. 재생성하면 이 폴더의 결과 파일을 다시 쓰므로 수정한 작업은 다른 이름으로 보관하세요.

## 형태 참고

[Pokémon Database의 Charizard artwork](https://pokemondb.net/artwork/charizard)와 로컬 [참고 이미지](reference/charizard_reference.jpg)를 형태와 색 참고용으로 사용했습니다. 참고 이미지에서 메시를 가져오지 않았습니다.
