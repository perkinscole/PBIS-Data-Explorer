"""Evidence-based PBIS action recommendations tied to data indicators."""

# Each category maps to a list of strategies with context
STRATEGY_DATABASE = {
    "safety": [
        {
            "title": "Implement Restorative Practices",
            "description": "Train staff in restorative circles and conflict resolution. Replace punitive discipline with conversations that repair harm and rebuild relationships.",
            "resources": "PBIS.org Restorative Practices Guide, International Institute for Restorative Practices",
        },
        {
            "title": "Create Safe Spaces",
            "description": "Designate calm-down rooms or safe spaces where students can go when feeling overwhelmed. Staff these with trained counselors or social workers.",
            "resources": "CASEL Safe Spaces Toolkit",
        },
        {
            "title": "Anti-Bullying Campaign",
            "description": "Launch a school-wide anti-bullying initiative with student leaders, clear reporting mechanisms, and regular check-ins.",
            "resources": "StopBullying.gov, Olweus Bullying Prevention Program",
        },
    ],
    "teacher_respect": [
        {
            "title": "Culturally Responsive Teaching PD",
            "description": "Provide professional development on culturally responsive teaching practices so all students feel seen and respected in the classroom.",
            "resources": "Zaretta Hammond's 'Culturally Responsive Teaching and the Brain'",
        },
        {
            "title": "Student Voice Initiatives",
            "description": "Create formal channels for student feedback — advisory councils, suggestion boxes, or regular student-teacher check-ins.",
            "resources": "Quaglia Institute for School Voice and Aspirations",
        },
        {
            "title": "Relationship-Building Practices",
            "description": "Implement 2x10 strategy (2 minutes of personal conversation with a student for 10 consecutive days) for students who feel disconnected from adults.",
            "resources": "PBIS 2x10 Strategy Guide",
        },
    ],
    "school_belonging": [
        {
            "title": "Advisory/Mentoring Program",
            "description": "Create small advisory groups where every student has a dedicated adult mentor who checks in regularly.",
            "resources": "AMLE Advisory Guide, Breaking Ranks in the Middle",
        },
        {
            "title": "Expand Extracurricular Offerings",
            "description": "Increase the variety of clubs, sports, and activities so every student can find their place. Focus on inclusive, low-barrier options.",
            "resources": "ASCD Whole Child Initiative",
        },
        {
            "title": "New Student Welcome Program",
            "description": "Assign peer buddies to new students, host orientation events, and check in during the first weeks of school.",
            "resources": "WestEd New Student Integration Research",
        },
    ],
    "student_respect": [
        {
            "title": "Peer Mediation Program",
            "description": "Train student mediators to help resolve conflicts between peers. Gives students ownership of school climate.",
            "resources": "National Association for Mediation in Education",
        },
        {
            "title": "Social Skills Groups",
            "description": "Run small-group sessions on empathy, communication, and conflict resolution for students who struggle with peer relationships.",
            "resources": "CASEL SEL Framework, Second Step Program",
        },
        {
            "title": "Upstander Training",
            "description": "Teach students to be upstanders (not bystanders) when they see disrespect or bullying. Build a culture where students hold each other accountable.",
            "resources": "ADL No Place for Hate, Sandy Hook Promise",
        },
    ],
    "care_values": [
        {
            "title": "CARE Values Refresh Campaign",
            "description": "Re-launch the CARE values with student-created content — videos, posters, morning announcements. Students internalize values better when they own them.",
            "resources": "PBIS Tier 1 Implementation Guide",
        },
        {
            "title": "Values-in-Action Recognition",
            "description": "Create specific recognition for students caught demonstrating each CARE value. Make it visible — hallway displays, assemblies, parent newsletters.",
            "resources": "PBIS Rewards Best Practices",
        },
    ],
    "behavior_support": [
        {
            "title": "Review Reward System",
            "description": "Survey students about what rewards they actually value. Shift from material rewards toward experiences and privileges.",
            "resources": "PBIS Rewards Research Brief",
        },
        {
            "title": "Consistency Training for Staff",
            "description": "Ensure all staff use the same language and procedures for behavior expectations. Inconsistency is one of the top reasons behavior systems fail.",
            "resources": "PBIS Tier 1 Fidelity Checklist",
        },
        {
            "title": "Family Engagement in Behavior Support",
            "description": "Send positive behavior reports home, not just negative ones. Invite families to understand and reinforce CARE values at home.",
            "resources": "Harvard Family Research Project",
        },
    ],
    "peer_connections": [
        {
            "title": "Cooperative Learning Structures",
            "description": "Use structured group work (Kagan structures, jigsaw method) to build peer relationships through academics.",
            "resources": "Kagan Cooperative Learning, Spencer Kagan",
        },
        {
            "title": "Cross-Grade Buddy Programs",
            "description": "Pair older students with younger ones for reading buddies, CARE value modeling, or transition support.",
            "resources": "Big Brothers Big Sisters School-Based Model",
        },
    ],
    "school_environment": [
        {
            "title": "Student-Led Environment Improvement",
            "description": "Empower students to take ownership of school spaces — bathroom monitors, cafeteria clean-up crews, hallway mural projects.",
            "resources": "ASCD School Climate Framework",
        },
        {
            "title": "Clear Expectations by Location",
            "description": "Create and teach specific behavior expectations for each school area (hallway, cafeteria, bathroom, playground). Post them visually.",
            "resources": "PBIS Teaching Matrix",
        },
    ],
    "success": [
        {
            "title": "Goal-Setting Workshops",
            "description": "Teach students to set academic and personal goals each quarter. Regular check-ins help them see their own growth.",
            "resources": "Growth Mindset Research (Carol Dweck), SMART Goals Framework",
        },
        {
            "title": "Strength-Based Feedback",
            "description": "Train staff to lead with what students are doing well before addressing areas for improvement. Shift from deficit to asset framing.",
            "resources": "Positive Psychology in Education, VIA Character Strengths",
        },
    ],
}


def generate_recommendations(category_scores, trend_changes=None, benchmark_gaps=None, at_risk=None):
    """Generate prioritized action recommendations based on data.

    Args:
        category_scores: dict of {category: avg_score} (1-4 scale)
        trend_changes: dict of {category: change_value} (optional)
        benchmark_gaps: dict of {indicator: gap_pct} (optional)
        at_risk: dict of {label: {count, total}} (optional)

    Returns list of recommendation dicts sorted by priority.
    """
    recommendations = []

    # 1. Flag lowest-scoring categories
    if category_scores:
        sorted_cats = sorted(category_scores.items(), key=lambda x: x[1])
        for cat, score in sorted_cats:
            if score < 2.5:
                priority = "high"
                finding = f"**{cat.replace('_', ' ').title()}** scores very low ({score:.2f}/4.0)"
            elif score < 3.0:
                priority = "medium"
                finding = f"**{cat.replace('_', ' ').title()}** scores below average ({score:.2f}/4.0)"
            else:
                continue

            strategies = STRATEGY_DATABASE.get(cat, [])
            for strategy in strategies[:2]:  # Top 2 strategies per category
                recommendations.append({
                    "priority": priority,
                    "finding": finding,
                    "why": f"Scores below 3.0 indicate many respondents disagree on {cat.replace('_', ' ')} questions.",
                    "action": strategy["title"],
                    "details": strategy["description"],
                    "resources": strategy["resources"],
                    "category": cat,
                })

    # 2. Flag biggest declines
    if trend_changes:
        for cat, change in sorted(trend_changes.items(), key=lambda x: x[1]):
            if change < -0.3:
                priority = "high" if change < -0.5 else "medium"
                strategies = STRATEGY_DATABASE.get(cat, [])
                if strategies:
                    recommendations.append({
                        "priority": priority,
                        "finding": f"**{cat.replace('_', ' ').title()}** declined by {abs(change):.2f} points",
                        "why": "A declining trend suggests something changed that needs attention.",
                        "action": strategies[0]["title"],
                        "details": strategies[0]["description"],
                        "resources": strategies[0]["resources"],
                        "category": cat,
                    })

    # 3. Flag benchmark gaps
    if benchmark_gaps:
        for indicator, gap in sorted(benchmark_gaps.items(), key=lambda x: x[1]):
            if gap < -10:
                cat_match = None
                ind_lower = indicator.lower()
                for cat in STRATEGY_DATABASE:
                    if cat.replace("_", " ") in ind_lower:
                        cat_match = cat
                        break
                if cat_match and STRATEGY_DATABASE.get(cat_match):
                    strategy = STRATEGY_DATABASE[cat_match][0]
                    recommendations.append({
                        "priority": "high" if gap < -15 else "medium",
                        "finding": f"**{indicator}** is {abs(gap):.0f}% below regional benchmark",
                        "why": "Being significantly below the MetroWest regional average indicates an area where RAMS is behind peer schools.",
                        "action": strategy["title"],
                        "details": strategy["description"],
                        "resources": strategy["resources"],
                        "category": cat_match,
                    })

    # Sort by priority (high first)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda r: priority_order.get(r["priority"], 2))

    # Deduplicate by action title
    seen_actions = set()
    unique = []
    for rec in recommendations:
        if rec["action"] not in seen_actions:
            seen_actions.add(rec["action"])
            unique.append(rec)

    return unique
