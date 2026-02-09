"""
Seed script for V1 manual testing.

Creates a demo scene + 5 agents with profiles, then prints
the scene_id for use in the frontend.

Usage:
    python scripts/seed_demo.py
"""

import httpx
import sys

BASE_URL = "http://localhost:8081/api"

SCENE = {
    "name": "寻找技术合伙人",
    "description": "一个创业者寻找能够一起构建 AI 产品的技术合伙人",
    "organizer_id": "user_default",
    "expected_responders": 5,
    "access_policy": "open",
}

AGENTS = [
    {
        "agent_id": "agent_alice",
        "display_name": "Alice",
        "source_type": "claude",
        "profile_data": {
            "bio": "Full-stack engineer with 6 years experience. Built 3 AI products from scratch. Former tech lead at a YC startup.",
            "skills": ["Python", "Machine Learning", "React", "System Design", "AWS"],
            "experience": "Led a team of 5 engineers building an AI-powered recommendation engine. Shipped products used by 100K+ users.",
            "interests": "AI product development, startup culture, technical leadership",
        },
    },
    {
        "agent_id": "agent_bob",
        "display_name": "Bob",
        "source_type": "claude",
        "profile_data": {
            "bio": "Backend specialist focused on distributed systems and data pipelines. 8 years in big tech.",
            "skills": ["Go", "Kubernetes", "PostgreSQL", "Kafka", "gRPC"],
            "experience": "Designed and operated a data pipeline processing 10M events/day at scale. Expert in reliability engineering.",
            "interests": "Infrastructure, scalability, open source contributions",
        },
    },
    {
        "agent_id": "agent_carol",
        "display_name": "Carol",
        "source_type": "claude",
        "profile_data": {
            "bio": "AI researcher turned product builder. PhD in NLP, now focused on applied AI.",
            "skills": ["PyTorch", "NLP", "LLM Fine-tuning", "Python", "Research"],
            "experience": "Published 5 papers on transformer architectures. Built a RAG system serving 50K queries/day.",
            "interests": "LLM applications, agent frameworks, AI safety",
        },
    },
    {
        "agent_id": "agent_dave",
        "display_name": "Dave",
        "source_type": "claude",
        "profile_data": {
            "bio": "Product designer and frontend engineer. Passionate about user experience and design systems.",
            "skills": ["Figma", "React", "TypeScript", "CSS", "User Research"],
            "experience": "Designed and built the UI for 2 successful SaaS products. Strong focus on accessibility and mobile-first design.",
            "interests": "Design systems, creative coding, human-computer interaction",
        },
    },
    {
        "agent_id": "agent_eve",
        "display_name": "Eve",
        "source_type": "claude",
        "profile_data": {
            "bio": "Blockchain and Web3 developer with startup experience. 2x founder.",
            "skills": ["Solidity", "Rust", "Move", "Smart Contracts", "DeFi"],
            "experience": "Co-founded a DeFi protocol with $5M TVL. Built on-chain governance systems.",
            "interests": "Decentralized systems, token economics, on-chain AI agents",
        },
    },
]


def main():
    with httpx.Client(timeout=10) as client:
        # 1. Create scene
        r = client.post(f"{BASE_URL}/scenes", json=SCENE)
        if r.status_code != 201:
            print(f"Failed to create scene: {r.status_code} {r.text}")
            sys.exit(1)
        scene_id = r.json()["scene_id"]
        print(f"Scene created: {scene_id}")

        # 2. Register agents
        for agent in AGENTS:
            r = client.post(f"{BASE_URL}/scenes/{scene_id}/agents", json=agent)
            if r.status_code != 201:
                print(f"Failed to register {agent['agent_id']}: {r.status_code} {r.text}")
                continue
            print(f"  Agent registered: {agent['display_name']} ({agent['agent_id']})")

        print()
        print(f"Done! Scene ID: {scene_id}")
        print(f"Use this in the frontend or curl:")
        print(f'  curl -X POST {BASE_URL}/negotiations/submit \\')
        print(f'    -H "Content-Type: application/json" \\')
        print(f'    -d \'{{"scene_id": "{scene_id}", "user_id": "user_default", "intent": "我需要一个技术合伙人来做 AI 产品"}}\'')


if __name__ == "__main__":
    main()
