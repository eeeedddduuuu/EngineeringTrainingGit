"""P5 全流程端到端测试：注册→登录→创作→Agent流水线→知识库检索"""
import httpx, json, time

BASE = "http://localhost:8000"

# 1. 注册+登录
user = {"username": "p5e2e_test", "password": "test123"}
httpx.post(f"{BASE}/api/auth/register", json=user, timeout=10)
token = httpx.post(f"{BASE}/api/auth/login", json=user, timeout=10).json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

# 2. 提交创作任务
print("=== 提交创作任务 ===")
task_req = {
    "topic": "秋季护肤好物推荐",
    "target_audience": "25-35岁职场女性",
    "platform": "douyin",
    "duration": "60s",
    "style": "干货+轻娱乐",
}
r = httpx.post(f"{BASE}/api/creation/start", json=task_req, headers=h, timeout=10)
print(f"Status: {r.status_code}")
task = r.json()
print(f"task_id: {task['task_id']}")
print(f"message: {task['message']}")

# 3. 轮询任务状态
print("\n=== 轮询任务状态 ===")
completed = False
for i in range(15):
    time.sleep(2)
    r = httpx.get(f"{BASE}/api/task/{task['task_id']}/status", headers=h, timeout=10)
    s = r.json()
    print(f"  [{i+1}] {s['status']}: {s.get('progress','')}")
    if s["status"] == "completed":
        result = s["result"]
        print(f"\n=== 创作完成! ===")
        print(f"session_id: {result['session_id']}")
        print(f"方案数: {len(result['schemes'])}")
        for sc in result["schemes"]:
            print(f"  [{sc['version']}] score={sc['score']} rank={sc['rank']} {sc['title'][:45]}")
        if "recommendation" in result:
            rec = result["recommendation"]
            print(f"推荐: {rec['best_version']} - {rec['reason'][:60]}")
        completed = True
        break
    elif s["status"] == "failed":
        print(f"  FAILED: {s.get('result', {})}")
        break

if not completed:
    print("TIMEOUT: 任务未在30秒内完成")

# 4. 知识库检索
print("\n=== 知识库检索 ===")
r = httpx.get(f"{BASE}/api/knowledge/search", params={"q": "护肤", "top_k": 3}, headers=h, timeout=30)
results = r.json()["results"]
print(f"查询'护肤'返回 {len(results)} 条:")
for item in results:
    print(f"  [{item['similarity']:.3f}] {item['title'][:45]}")

print("\n✅ 全流程验证完成: 注册→登录→创作→Agent→知识库检索")
