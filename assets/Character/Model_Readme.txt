Blender 여성 모험가 3D 모델

열기
프로젝트 루트의 Open_Blender_Character.cmd를 실행합니다.
실제 모델 파일은 assets/Character/Adventurer_Model_v001.blend입니다.
원화만 들어 있는 Character_References_v003.blend와 다른 파일입니다.
수정 전 File > Save As로 Adventurer_Work_v002.blend처럼 새 이름을 저장하세요.

구성
03_Character_Work: 몸체, 눈, 눈썹·속눈썹, 단발, 셔츠, 조끼, 바지, 부츠,
벨트, 작은 주머니, 별도 검이 있습니다. 각 부위를 따로 선택하고 편집할 수 있습니다.
Body_Female_Edit가 몸체입니다. Subdivision을 적용하지 않아 기본 면을 편집할 수 있습니다.
04_Rig: Adventurer_Rig는 기본 FK 골격입니다. 기본 화면에서는 숨겨져 있습니다.
05_Studio: 미리보기 카메라, 조명, 바닥입니다. 게임 캐릭터의 일부가 아닙니다.
01_Reference: 이전에 확정한 AI 원화 3장이 들어 있습니다.
02_Source_High: 의상 제작용 원본 보조 메시입니다. 렌더링에서 제외했습니다.

기본 편집
원하는 메시를 선택하고 Tab으로 Edit Mode에 들어갑니다.
G/R/S로 이동·회전·크기를 조절합니다. 한 부위의 비율부터 조금씩 수정하세요.
머리카락은 덩어리별로 나뉘어 있습니다. 정면과 측면을 번갈아 보며 수정하세요.
Material Properties에서 피부, 청록색 천, 갈색 가죽 등의 색과 거칠기를 바꿀 수 있습니다.
입술과 볼 색은 몸체의 FaceTint 색상 속성입니다. 피부 재질에서 이 속성을 읽습니다.

골격과 포즈
Outliner의 04_Rig에서 Adventurer_Rig 숨김을 해제하고 선택합니다.
Pose Mode에서 UpperArm.L, Forearm.L, Thigh.L 등의 뼈를 회전해 보세요.
L/R은 캐릭터 자신의 왼쪽/오른쪽입니다. Alt+R로 선택한 뼈의 회전을 초기화합니다.
기본 골격과 초기 웨이트를 연결했습니다. 정밀한 관절 변형, 극단적인 포즈의 옷 관통,
얼굴 표정 리그는 후속 작업입니다. 검은 독립 소품으로 두고 미리보기 렌더에서는 숨겼습니다.

현재 제작 단계
AI 원화를 참고해 실제 편집 가능한 3D 메시로 만든 첫 모델입니다.
MakeHuman의 CC0 인체 바탕에 여성 체형을 적용하고 머리·의상·장비·얼굴 표현을 제작했습니다.
Tripo에서 생성한 메시가 아니며, 원화의 얼굴과 모든 세부를 자동 복제한 모델도 아닙니다.
UV는 인체와 원본을 사용한 의상에 있습니다. 최종 텍스처 베이크·LOD·엔진 최적화는 후속 단계입니다.
Blender 렌더 미리보기와 기본 팔 포즈 시험 결과를 PNG와 Adventurer_Validation.json에 기록합니다.

재현
scripts/build_adventurer.py가 생성 모델과 미리보기를 다시 만듭니다.
같은 출력 파일을 다시 쓰므로 직접 수정한 파일은 반드시 다른 이름으로 보관하세요.
scripts/verify_adventurer.py는 저장 파일 재열기, 메시와 웨이트, 팔 포즈 변형을 검사합니다.
검사 과정의 임시 포즈는 모델 파일에 저장하지 않습니다.

출처
Source/MakeHuman/sourceurls.txt: 고정된 원본 주소와 라이선스.
Source/MakeHuman/manifest.json: 내려받은 데이터의 SHA-256.
Source/MakeHuman/LICENSE.ASSETS.md: CC0 자산 라이선스.
References/Generation_Prompts_v003.txt: 참고 원화를 만든 내장 이미지 생성 도구의 프롬프트.
