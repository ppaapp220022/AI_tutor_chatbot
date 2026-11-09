import os

# 평가는 DB에 닿지 않는다. app.backend.database가 import 시점에 DATABASE_URL을 요구해서 자리값만 넣는다(연결하지 않음)
os.environ.setdefault("DATABASE_URL", "postgresql://eval:eval@localhost:5432/unused")
