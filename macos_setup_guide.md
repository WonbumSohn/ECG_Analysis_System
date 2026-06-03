# macOS 정적 분석 도구 설치 가이드

> **이 파일은 Claude Code(Cursor 내)가 읽고 순서대로 실행하기 위한 가이드입니다.**
> 모든 명령어는 macOS 터미널(bash/zsh)에서 실행합니다.

---

## 0단계: 사전 확인

### Homebrew 설치 확인
```bash
brew --version
```
- **미설치 시** 아래 명령어로 Homebrew를 먼저 설치:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
- Apple Silicon(M1/M2/M3/M4) Mac인 경우 설치 후 PATH 설정 필요:
```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### conda 설치 확인
```bash
conda --version
```
- conda가 설치되어 있으면 Python 도구는 conda로 설치 (1단계-A)
- conda가 없으면 pip로 설치 (1단계-B)

---

## 1단계: Python 도구 설치

### 1단계-A: conda가 있는 경우
```bash
conda install -y black ruff pre-commit pylint
```

### 1단계-B: conda가 없는 경우 (pip 사용)
```bash
pip install black ruff pre-commit pylint
```

### 설치 확인
```bash
black --version
ruff version
pre-commit --version
pylint --version
```

---

## 2단계: C/C++ 도구 설치

### clang-tidy (LLVM 패키지에 포함)
```bash
brew install llvm
```
- **중요**: Homebrew의 LLVM은 시스템 기본 PATH에 들어가지 않으므로, clang-tidy를 사용하려면 PATH 설정이 필요합니다.

#### Apple Silicon Mac (M1/M2/M3/M4)
```bash
echo 'export PATH="/opt/homebrew/opt/llvm/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Intel Mac
```bash
echo 'export PATH="/usr/local/opt/llvm/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### cppcheck
```bash
brew install cppcheck
```

### 설치 확인
```bash
clang-tidy --version
cppcheck --version
```

---

## 3단계: Java/JDK 설치 (Kotlin 도구 선행 요건)

```bash
brew install openjdk@21
```

설치 후 시스템에서 인식하도록 심볼릭 링크 생성:
```bash
sudo ln -sfn $(brew --prefix openjdk@21)/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-21.jdk
```

### 설치 확인
```bash
java -version
```

---

## 4단계: Kotlin 도구 설치

### ktlint
```bash
brew install ktlint
```

### detekt
```bash
brew install detekt
```

### 설치 확인
```bash
ktlint --version
detekt-cli --version
```

---

## 5단계: 데이터베이스(SQL) 도구 설치

### sqlfluff (SQL 린터 + 포맷터)

conda가 있는 경우:
```bash
conda install -y sqlfluff
```
conda에 없거나 conda가 없는 경우:
```bash
pip install sqlfluff
```

### sqlcheck (SQL 안티패턴 탐지)
```bash
brew install sqlcheck
```

### squawk (PostgreSQL 마이그레이션 린터)
```bash
brew install squawk
```

### 설치 확인
```bash
sqlfluff version
sqlcheck --help | head -1
squawk --version
```

---

## 6단계: 최종 전체 확인

아래 명령어를 실행하여 모든 도구가 정상 설치되었는지 확인합니다:

```bash
echo "========== 설치 확인 결과 =========="
echo ""
echo "--- Python 도구 ---"
echo "Black:       $(black --version 2>&1 | head -1)"
echo "Ruff:        $(ruff version 2>&1)"
echo "pre-commit:  $(pre-commit --version 2>&1)"
echo "pylint:      $(pylint --version 2>&1 | head -1)"
echo ""
echo "--- C/C++ 도구 ---"
echo "clang-tidy:  $(clang-tidy --version 2>&1 | head -1)"
echo "cppcheck:    $(cppcheck --version 2>&1)"
echo ""
echo "--- Java ---"
echo "Java:        $(java -version 2>&1 | head -1)"
echo ""
echo "--- Kotlin 도구 ---"
echo "ktlint:      $(ktlint --version 2>&1)"
echo "detekt:      $(detekt-cli --version 2>&1)"
echo ""
echo "--- DB 도구 ---"
echo "sqlfluff:    $(sqlfluff version 2>&1)"
echo "sqlcheck:    $(sqlcheck --version 2>&1 || echo 'installed (no --version flag)')"
echo "squawk:      $(squawk --version 2>&1)"
echo ""
echo "===================================="
```

---

## 설치 도구 요약

| 도구 | 언어 | 역할 | 설치 방법 |
|------|------|------|-----------|
| Black | Python | 코드 포맷터 | conda/pip |
| Ruff | Python | 린터 + 포맷터 | conda/pip |
| pre-commit | 전체 | Git hook 관리 | conda/pip |
| pylint | Python | 린터 | conda/pip |
| clang-tidy | C/C++ | 코드 모던화/변환 | brew (LLVM) |
| cppcheck | C/C++ | 버그/메모리 누수 탐지 | brew |
| OpenJDK 21 | Java | Kotlin 도구 선행 요건 | brew |
| ktlint | Kotlin | 스타일/포맷팅 | brew |
| detekt | Kotlin | 코드 스멜/복잡도 분석 | brew |
| sqlfluff | SQL | SQL 린터 + 포맷터 | conda/pip |
| sqlcheck | SQL | SQL 안티패턴 탐지 | brew |
| squawk | SQL(PostgreSQL) | 마이그레이션 린터 | brew |

---

## 트러블슈팅

### brew 명령어를 찾을 수 없는 경우
```bash
eval "$(/opt/homebrew/bin/brew shellenv)"  # Apple Silicon
# 또는
eval "$(/usr/local/bin/brew shellenv)"     # Intel
```

### clang-tidy를 찾을 수 없는 경우
```bash
# Apple Silicon
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
# Intel
export PATH="/usr/local/opt/llvm/bin:$PATH"
```

### java를 찾을 수 없는 경우
```bash
sudo ln -sfn $(brew --prefix openjdk@21)/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-21.jdk
```

### detekt-cli를 찾을 수 없는 경우
```bash
# brew로 설치 시 detekt-cli가 아닌 detekt로 실행될 수 있음
detekt --version
```
