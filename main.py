"""배포용 진입점.

Railpack/Nixpacks 등 자동 빌더는 프로젝트 루트의 main.py 를 찾아 FastAPI 앱을
uvicorn 으로 실행한다. 실제 앱은 webapp.py 에 정의되어 있고 여기서 그대로 가져온다.

    - `uvicorn main:app` 으로도 실행되고,
    - `python main.py` 로 직접 실행해도 서버가 뜬다.
"""

from __future__ import annotations

import os

from webapp import app  # noqa: F401  (uvicorn main:app 진입점)

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
