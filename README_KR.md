# gfl2logger

[English](README.md) | 한국어

`gfl2logger`는 소녀전선 2: 망명(Girls' Frontline 2: Exilium)이 서버에서 받는
데이터를 읽어, 서클 멤버 목록·활동 기록·보유 장비처럼 보관할 가치가 있는 부분을
로컬 CSV 및 JSON 파일로 저장합니다. **Windows**와 **macOS**를 하나의 코드로
지원하며, 두 플랫폼에서 기능·옵션·창 구성이 동일합니다.

## 다운로드

| 플랫폼 | 게임 클라이언트 | 다운로드 (v0.3.0) |
| --- | --- | --- |
| **Windows** (x64) | PC 클라이언트 | [`gfl2logger-v0.3.0-windows-x64.zip`](../../releases/download/v0.3.0/gfl2logger-v0.3.0-windows-x64.zip) |
| **macOS** (Apple Silicon) | Mac App Store의 iPhone/iPad 버전 | [`gfl2logger-v0.3.0-macos-arm64.dmg`](../../releases/download/v0.3.0/gfl2logger-v0.3.0-macos-arm64.dmg) · [`gfl2logger-v0.3.0-macos-arm64.zip`](../../releases/download/v0.3.0/gfl2logger-v0.3.0-macos-arm64.zip) |

이전 버전과 릴리스 노트는 [Releases](../../releases) 페이지에 있습니다.

## 시작하기

게임보다 **먼저** `gfl2logger`를 실행합니다. 게임이 이미 실행 중이라면 로거
창이 열린 뒤 게임을 다시 시작합니다.

### Windows

1. `.zip`을 내려받아 쓰기 권한이 있는 폴더에 압축을 풉니다. `_internal` 폴더는
   `gfl2logger.exe`와 같은 위치에 그대로 둡니다.
2. `gfl2logger.exe`를 실행합니다. 코드 서명이 없어 Windows SmartScreen이
   **Windows의 PC 보호** 화면을 표시할 수 있습니다. 이 저장소의 Releases
   페이지에서 받은 파일이라면 **추가 정보 > 실행**을 선택합니다.
3. mitmproxy의 트래픽 리디렉터에 대해 Windows가 관리자 권한을 요청하면
   허용합니다.

내보낸 파일은 프로그램을 실행한 폴더에 저장됩니다. 나중에 `WinDivert64.sys`가
사용 중이라는 이유로 폴더를 삭제하거나 교체할 수 없다면 Windows를 다시 시작한 뒤
시도하십시오. 캡처 드라이버는 프로그램을 닫은 뒤에도 로드된 상태로 남을 수
있습니다.

### macOS

1. `.dmg`를 열어 `gfl2logger.app`을 **응용 프로그램**으로 드래그하거나, `.zip`의
   압축을 풉니다.
2. 앱을 엽니다. 임시(ad-hoc) 서명 상태이고 Apple Developer ID 공증을 받지 않아,
   처음 실행하면 **“gfl2logger”이(가) 열리지 않음** 경고와 함께 차단됩니다.
   **완료**를 클릭한 뒤 **시스템 설정 > 개인정보 보호 및 보안**을 열고
   **보안**까지 스크롤하여 **그래도 열기**를 클릭합니다. 이 버튼은 차단된 실행
   시도 후 약 1시간 동안 표시되며, 한 번 승인하면 macOS가 예외로 기억합니다.
   자세한 내용은
   [Apple 공식 안내](https://support.apple.com/ko-kr/guide/mac-help/mchleab3a043/mac)를
   참조하십시오. 이 저장소의 Releases 페이지에서 받은 파일에만 적용하십시오.
3. macOS가 네트워크 확장 프로그램 권한을 요청하면 **Mitmproxy Redirector**를
   승인합니다. 자동으로 활성화되지 않으면 **시스템 설정 > 일반 > 로그인 항목 및
   확장 프로그램 > 네트워크 확장 프로그램**에서 켠 다음 `gfl2logger`를 다시
   실행합니다.

번들로 제공되는 네트워크 리디렉터는 mitmproxy 프로젝트가 별도로 서명하고
공증했습니다.

## 사용법

1. 저장하려는 데이터의 체크박스를 켜 둡니다. **Save config**를 누르면 다음
   실행에도 선택이 유지됩니다.
2. 게임을 실행해 로그인합니다. 서클 데이터는 서클 페이지를 열면 수신됩니다.
3. 게임이 지원 대상 응답을 받을 때마다 새 파일이 기록되고, 오른쪽 로그에 저장
   경로가 표시됩니다.
4. 창을 닫으면 프로그램이 완전히 종료됩니다. 백그라운드에 남는 프로세스는
   없습니다.

| 플랫폼 | 내보낸 파일과 `gfl2logger.config.yaml`의 저장 위치 |
| --- | --- |
| Windows | 프로그램을 실행한 폴더(보통 `gfl2logger.exe`가 있는 폴더) |
| macOS | `~/gfl2logger` |

### 내보내는 데이터

창에서 옵션은 두 그룹으로 나뉘어 표시됩니다.

| 그룹 | 옵션 | 페이로드 | 설명 | 수신 시점 | 형식 |
| --- | --- | ---: | --- | --- | --- |
| Platoon | Platoon Profile | `21905` | 서클 식별 정보, 레벨, 멤버 수, 공지 및 모집 안내 | 서클 페이지 | JSON |
| Platoon | Members | `21917` | 멤버 이름, UID, 레벨, 공적치, 점수 및 로그인 시간 | 로그인, 재접속, 서클 페이지 | CSV |
| Platoon | Activity | `21935` | 서클 목표 및 최근 멤버 활동 | 서클 페이지 | JSON |
| Platoon | Updates | `21960` | 동향 탭의 멤버 가입/탈퇴/추방 및 과업 보급 생성 기록 | 동향 탭 | JSON |
| Others | Weapons | `11021` | 현재 계정이 보유한 무기 | 로그인 | CSV |
| Others | Attachments | `11061` | 현재 계정이 보유한 파츠 | 로그인 | CSV |
| Others | Common Keys | `11138` | 현재 계정이 보유한 공용키 | 로그인 | CSV |
| Others | Formations | `23201` | 저장된 편성 | 로그인, 재접속 | JSON |

파일 이름은 `gfl2logger_<종류>_<UTC 시각>.csv` 또는 `.json` 형식입니다. Updates는
protobuf 필드 번호와 원본 hex로 손실 없이 기록됩니다.

## 작동 방식

mitmproxy의 로컬 캡처 모드로 가로채기 대상을 게임 실행 파일로 제한합니다.
Windows에서는 `GF2_Exilium`, macOS에서는 `SnqxExilium`입니다. 로거는 서버가
클라이언트로 보내는 데이터만 읽습니다. 연결을 새로 만들거나 변경하지 않으며,
TLS 연결은 복호화하지 않고 그대로 통과시키므로 인증서를 설치할 필요가
없습니다.

## 지원 클라이언트

- **Windows:** PC 클라이언트. Darkwinter 및 HaoPlay 지역에서 동작이
  확인되었습니다.
- **macOS:** Apple Silicon Mac에서 실행되는 iPhone/iPad App Store 버전.

그 외 플랫폼과 지역은 테스트되지 않았습니다. 추가 데이터, 사용 방식, 형식에 대한
제안을 환영합니다.

## 소스에서 빌드하기

이 프로젝트는 [PDM](https://pdm-project.org/)과 Python 3.13을 사용합니다. 이
저장소를 클론한 폴더에서 다음을 실행합니다.

```sh
pdm install
pdm run pyinstaller
```

Windows에서는 `dist/gfl2logger/gfl2logger.exe`, macOS에서는
`dist/gfl2logger.app`이 생성됩니다. 소스에서 직접 실행하거나 테스트를 돌리려면 다음 명령을 사용합니다.

```sh
pdm run protoc
pdm run python main.py
pdm run python -m unittest discover -s tests
```

`v*.*.*` 태그를 푸시하면 두 플랫폼을 모두 빌드해 하나의 릴리스로 게시합니다.

## 크레딧

`gfl2logger`는 [blead](https://github.com/blead)가 만들었습니다. 패킷 파서, 데이터
내보내기 기능, 원본 Windows 애플리케이션이 여기에 해당합니다. macOS 지원,
Platoon Profile·Activity·Updates 내보내기, 파서와 내보내기의 안정성 보강은
[1window2/gf2logger](https://github.com/1window2/gf2logger) 포크에서
개발되었습니다.

## 라이선스

MIT (`pyproject.toml`에 명시).
