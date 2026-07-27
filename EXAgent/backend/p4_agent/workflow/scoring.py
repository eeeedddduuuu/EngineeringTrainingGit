"""
候选方案评分算法 — 5 维度量化评分，不能直接用 LLM 说"这个好"
"""

from __future__ import annotations

from typing import Any


# 评分维度与权重
SCORING_DIMENSIONS = [
    {"name": "开头钩子吸引力", "key": "hook_score", "weight": 0.25, "description": "前3秒能否抓住注意力"},
    {"name": "结构与平台匹配度", "key": "structure_score", "weight": 0.20, "description": "时长、节奏、格式是否符合平台规范"},
    {"name": "目标受众匹配度", "key": "audience_score", "weight": 0.20, "description": "内容风格、语言是否契合目标受众"},
    {"name": "内容原创性", "key": "originality_score", "weight": 0.15, "description": "与知识库中已有内容的差异化程度"},
    {"name": "可执行性", "key": "feasibility_score", "weight": 0.20, "description": "拍摄难度、成本、场景复杂度是否合理"},
]

# 评分范围
SCORE_RANGE = (0, 10)


def score_scheme(scheme: dict[str, Any]) -> dict[str, Any]:
    """
    对单个候选方案进行评分。

    输入格式（兼容旧格式 + Parser 产出格式）:

    # 旧格式（手动构造，demo scoring 用）
    scheme = {
        "version": "A",
        "hook": "开头钩子文案",
        "structure": "脚本结构描述",
        "audience_match": "是否匹配目标受众的评估",
        "content": "完整内容",
        "feasibility": "可执行性描述",
    }

    # Parser 产出格式（与 P3 Scheme 表对齐）
    scheme = {
        "version": "A",
        "title": "...",
        "hook": "...",
        "scenes": [{"seq":1, "time":"0-3s", "type":"钩子", "content":"..."}],
        "hashtags": ["#tag1"],
        "cover_text": "...",
    }

    评分函数会自动检测并适配两种格式。

    输出: 附加评分字段
    """
    scores: dict[str, float] = {}

    # 1. 开头钩子吸引力评分
    hook = str(scheme.get("hook", ""))
    hook_score = _score_hook(hook)
    scores["hook_score"] = hook_score

    # 2. 结构匹配度评分
    structure = str(scheme.get("structure", ""))
    if not structure:
        # 兼容 Parser 输出：从 scenes 列表推导结构
        scenes = scheme.get("scenes", [])
        structure = f"{len(scenes)}个场景片段"
    structure_score = _score_structure(structure)
    scores["structure_score"] = structure_score

    # 3. 受众匹配度评分
    audience_info = str(scheme.get("audience_match", ""))
    if not audience_info:
        # 兼容：从 title + hook 间接评估
        audience_info = f"{scheme.get('title', '')} {scheme.get('hook', '')}"
    scores["audience_score"] = _score_audience(audience_info)

    # 4. 原创性评分
    content = str(scheme.get("content", ""))
    if not content:
        # 兼容：从 title + hook + scenes 文本评估
        scenes = scheme.get("scenes", [])
        scenes_text = " ".join(s.get("content", "") for s in scenes)
        content = f"{scheme.get('title', '')} {scheme.get('hook', '')} {scenes_text}"
    scores["originality_score"] = _score_originality(content)

    # 5. 可执行性评分
    feasibility = str(scheme.get("feasibility", ""))
    if not feasibility:
        # 兼容：从 scenes 复杂度评估
        scenes = scheme.get("scenes", [])
        feasibility = f"{len(scenes)}个场景" + ("，单人口播简单" if len(scenes) <= 3 else "，多场景切换复杂")
    scores["feasibility_score"] = _score_feasibility(feasibility)

    # 加权总分
    total = sum(
        scores.get(d["key"], 5) * d["weight"]
        for d in SCORING_DIMENSIONS
    )

    return {
        **scheme,
        "scores": scores,
        "total_score": round(total, 2),
        "scoring_method": "5维度加权评分",
    }


def _score_hook(hook: str) -> float:
    """评估开头钩子的吸引力。"""
    if not hook:
        return 3.0
    score = 5.0
    # 加分项
    if any(kw in hook for kw in ["你知道吗", "震惊", "居然", "竟然", "错了"]):
        score += 1.5  # 疑问/反差句式
    if any(kw in hook for kw in ["我", "你", "他"]):
        score += 1.0  # 有人称代入感
    if len(hook) < 30:
        score += 1.0  # 简洁有力
    if any(kw in hook for kw in ["数字", "数据", "年", "万"]):
        score += 0.5  # 有具体数据
    # 扣分项
    if len(hook) > 100:
        score -= 1.5  # 太啰嗦
    return max(1, min(10, score))


def _score_structure(structure: str) -> float:
    """评估脚本结构与平台规范的匹配度。"""
    if not structure:
        return 3.0
    score = 5.0
    # 加分：有时间分段
    if any(kw in structure for kw in ["0-", "s", "秒", "分"]):
        score += 2.0
    # 加分：有明确的起承转合
    if any(kw in structure for kw in ["开头", "结尾", "高潮", "引入"]):
        score += 1.5
    # 加分：标注了镜头类型
    if any(kw in structure for kw in ["特写", "中景", "远景", "全景"]):
        score += 1.5
    return max(1, min(10, score))


def _score_audience(audience_info: str) -> float:
    """评估受众匹配度。"""
    if not audience_info:
        return 5.0
    score = 5.0
    if any(kw in audience_info for kw in ["契合", "匹配", "适合", "目标"]):
        score += 3.0
    if any(kw in audience_info for kw in ["年龄", "性别", "兴趣", "需求"]):
        score += 2.0
    return max(1, min(10, score))


def _score_originality(content: str) -> float:
    """评估内容原创性。"""
    if not content:
        return 5.0
    score = 6.0
    # 加分：有独特角度
    if len(content) > 200:
        score += 1.0
    if any(kw in content for kw in ["独特", "不同", "创新", "新角度"]):
        score += 1.5
    # 扣分：大量通用词
    generic_count = sum(1 for w in ["首先", "然后", "最后", "总之", "所以"] if w in content)
    if generic_count > 3:
        score -= 1.5
    return max(1, min(10, score))


def _score_feasibility(feasibility: str) -> float:
    """评估可执行性。"""
    if not feasibility:
        return 5.0
    score = 6.0
    if any(kw in feasibility for kw in ["简单", "容易", "低成本", "手机", "单机"]):
        score += 2.0
    if any(kw in feasibility for kw in ["复杂", "团队", "专业设备", "预算", "特效"]):
        score -= 2.0
    return max(1, min(10, score))


def rank_schemes(schemes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """对多个方案评分并排序，返回排名结果。"""
    # 如果已有 total_score（DeepSeek 自带评分），保留原始评分
    has_scores = all("total_score" in s for s in schemes)
    if has_scores:
        for s in schemes:
            # 映射 total_score → score（API schema 字段名）
            s["score"] = s.get("total_score", s.get("score", 5.0))
        ranked = sorted(schemes, key=lambda s: s["total_score"], reverse=True)
        for i, s in enumerate(ranked):
            s["rank"] = i + 1
        if ranked:
            ranked[0]["recommendation_reason"] = f'综合得分最高（{ranked[0]["total_score"]}分）'
        return ranked

    scored = [score_scheme(s) for s in schemes]
    ranked = sorted(scored, key=lambda s: s["total_score"], reverse=True)
    for i, s in enumerate(ranked):
        s["rank"] = i + 1
        s["score"] = s.get("total_score", 5.0)
    if ranked:
        ranked[0]["recommendation"] = {
            "best": ranked[0].get("version", "?"),
            "reason": f"综合得分最高（{ranked[0]['total_score']}分），"
                      f"五个维度中「{SCORING_DIMENSIONS[0]['name']}」得分突出。",
        }
    return ranked


def scoring_report(ranked_schemes: list[dict[str, Any]]) -> str:
    """生成评分对比报告（Markdown），含每个方案各维度的迭代建议。"""
    lines = [
        "## 候选方案评分报告",
        "",
        f"| 方案 | 总分 | " + " | ".join(d["name"] for d in SCORING_DIMENSIONS) + " |",
        "|------|------|" + "|".join("------" for _ in SCORING_DIMENSIONS) + "|",
    ]
    for s in ranked_schemes:
        scores = s.get("scores", {})
        row = (
            f"| {s.get('version', '?')} "
            f"| {s.get('total_score', 0):.1f} "
            + "".join(f"| {scores.get(d['key'], 5):.1f} " for d in SCORING_DIMENSIONS)
            + "|"
        )
        lines.append(row)
    if ranked_schemes:
        best = ranked_schemes[0]
        rec = best.get("recommendation", {})
        lines.append("")
        lines.append(f"**推荐方案: {rec.get('best', '?')}**")
        lines.append(f"**理由: {rec.get('reason', '')}**")

    # 迭代建议：对每个方案的低分维度生成建议
    lines.append("")
    lines.append("## 迭代优化建议")
    lines.append("")
    for s in ranked_schemes:
        ver = s.get("version", "?")
        scores = s.get("scores", {})
        total = s.get("total_score", 0)
        weaknesses = []

        for d in SCORING_DIMENSIONS:
            key = d["key"]
            dim_score = scores.get(key, 5)
            if dim_score < 6:
                weaknesses.append((d["name"], dim_score, _suggest_improvement(key, dim_score)))

        if weaknesses:
            lines.append(f"### 方案 {ver}（总分 {total:.1f}）")
            lines.append("")
            for dim_name, score_val, suggestion in weaknesses:
                lines.append(f"- **{dim_name}**（{score_val:.1f}分）：{suggestion}")
            lines.append("")
        else:
            lines.append(f"### 方案 {ver}（总分 {total:.1f}）")
            lines.append("所有维度表现均衡，建议根据实际拍摄反馈微调。")
            lines.append("")

    return "\n".join(lines)


def _suggest_improvement(dim_key: str, score: float) -> str:
    """根据评分维度和得分生成具体迭代建议。"""
    suggestions = {
        "hook_score": {
            (0, 4): "开头太平淡，建议加入疑问句或反差句式，制造好奇缺口。",
            (4, 6): "钩子有一定吸引力但不够强，尝试在开头加入具体数字或人物代入。",
            (6, 8): "钩子不错，可进一步缩短到30字以内，增强前3秒的冲击力。",
            (8, 11): "钩子优秀，保持此风格。",
        },
        "structure_score": {
            (0, 4): "结构缺失，建议参照平台模板补充时间分段，标注每段的镜头类型和时长。",
            (4, 6): "结构有雏形但缺细节，加上起承转合标注，明确每段时长。",
            (6, 8): "结构较完整，可补充景别标注和运镜建议。",
            (8, 11): "结构规范完整，可考虑增加一个出人意料的转折点提升完播率。",
        },
        "audience_score": {
            (0, 4): "内容与目标受众脱节，重新审视受众画像，调整语言风格和切入角度。",
            (4, 6): "基本匹配但针对性不够，在文案中加入受众熟悉的行业用语或生活场景。",
            (6, 8): "受众匹配度尚可，可针对特定人群增加更精准的兴趣标签和场景化描述。",
            (8, 11): "受众定位精准，根据评论反馈持续优化即可。",
        },
        "originality_score": {
            (0, 4): "内容同质化严重，参考知识库中同类案例后，找到一个独特的切入角度或对比视角。",
            (4, 6): "有一定差异但不够突出，尝试加入个人经历、独家数据或反常识观点。",
            (6, 8): "原创性良好，可进一步强化个人风格或品牌调性。",
            (8, 11): "内容独特，注意知识产权保护和首发优势。",
        },
        "feasibility_score": {
            (0, 4): "执行难度过高或成本不现实，简化场景、减少演员、使用手机拍摄替代专业设备。",
            (4, 6): "有一定执行门槛，考虑将复杂场景拆分为多次拍摄，或使用替代方案降低预算。",
            (6, 8): "可执行性较好，制定详细的拍摄清单和备用方案以应对意外。",
            (8, 11): "极易落地，保持低成本高效率的优势。",
        },
    }

    mapping = suggestions.get(dim_key, {})
    for (lo, hi), text in mapping.items():
        if lo <= score < hi:
            return text
    return "建议针对此维度进一步优化。"
