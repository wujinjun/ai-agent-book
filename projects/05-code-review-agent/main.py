"""项目 5 入口：默认审查固定 Diff；传入 --repo 可读取真实 Git 工作区。"""

import argparse
from pathlib import Path

from ai_agent_book.apps.code_review import (
    CodeReviewService,
    GitRepository,
    HeuristicSemanticReviewer,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--base", default="HEAD")
    args = parser.parse_args()
    diff = (
        GitRepository(args.repo).diff(args.base)
        if args.repo
        else "diff --git a/app.py b/app.py\n+++ b/app.py\n@@ -0,0 +1 @@\n+API_KEY = 'demo'"
    )
    report = CodeReviewService(HeuristicSemanticReviewer()).review(diff)
    print(report.markdown)


if __name__ == "__main__":
    main()
