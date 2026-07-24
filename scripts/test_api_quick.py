"""快速验证后端 API 是否正常"""
import httpx
import json

BASE = "http://localhost:8000"

print("=" * 50)
print("1. 根路径")
r = httpx.get(BASE, timeout=10)
print(f"   {r.status_code}: {r.json()['message']}")

print("\n" + "=" * 50)
print("2. 知识库检索: q=短视频脚本, top_k=3")
r = httpx.get(f"{BASE}/api/knowledge/search", params={"q": "短视频脚本", "top_k": 3}, timeout=30)
print(f"   Status: {r.status_code}")
data = r.json()
for i, item in enumerate(data["results"], 1):
    print(f"   {i}. [sim={item['similarity']:.3f}] {item['title'][:40]}... | {item['platform']}")

print("\n" + "=" * 50)
print("3. 知识库检索: q=游戏策划角色设计, top_k=3")
r = httpx.get(f"{BASE}/api/knowledge/search", params={"q": "游戏策划角色设计", "top_k": 3}, timeout=30)
for i, item in enumerate(r.json()["results"], 1):
    print(f"   {i}. [sim={item['similarity']:.3f}] {item['title'][:40]}...")

print("\n" + "=" * 50)
print("4. 统计数据")
r = httpx.get(f"{BASE}/api/stats/samples", timeout=10)
data = r.json()
print(f"   总样本: {data['total_samples']}")
print(f"   主题: {[(t['name'], t['count']) for t in data['topic_distribution']]}")
print(f"   平台: {[(p['platform'], p['count']) for p in data['platform_distribution']]}")
print(f"   月度趋势: {len(data['monthly_trends'])} 个月")

print("\n" + "=" * 50)
print("5. 用户注册")
r = httpx.post(f"{BASE}/api/auth/register", json={
    "username": "test_p5", "password": "p5test123", "email": "p5@test.com"
}, timeout=10)
print(f"   Status: {r.status_code}")
print(f"   Body: {json.dumps(r.json(), ensure_ascii=False)}")

print("\n" + "=" * 50)
print("6. 用户登录")
r = httpx.post(f"{BASE}/api/auth/login", json={
    "username": "test_p5", "password": "p5test123"
}, timeout=10)
print(f"   Status: {r.status_code}")
data = r.json()
print(f"   Token: {data.get('access_token', 'N/A')[:50]}...")

print("\n✅ 全部接口验证完成！")
