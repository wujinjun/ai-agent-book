"""项目 9 入口：运行五角色、中心化状态和硬预算的开发团队。"""

import json

from ai_agent_book.apps.multi_agent_team import DevelopmentTeam

if __name__ == "__main__":
    result = DevelopmentTeam(max_messages=5, token_budget=2_000).run("增加健康检查")
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
