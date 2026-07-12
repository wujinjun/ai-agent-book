from ai_agent_book.apps.code_review import CodeReviewService, HeuristicSemanticReviewer


def test_added_secret_is_reported() -> None:
    diff = "+++ b/app.py\n@@ -0,0 +1 @@\n+API_KEY = 'secret'"
    report = CodeReviewService(HeuristicSemanticReviewer()).review(diff)
    assert report.findings[0].rule == "hardcoded-secret"
